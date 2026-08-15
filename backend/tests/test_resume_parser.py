"""简历解析规则提取 + 规则/LLM 融合 + 降级测试（成员A）。

验证：
1. 规则提取能抓邮箱/手机/学历/经验年限/技能词库/学校
2. 技能词库边界：紧贴中文的写法、避免 Java/JavaScript 误配
3. LLM 失败/返回脏数据时降级为规则结果（不抛异常）
4. LLM 成功时与规则结果正确融合（规则字段优先、技能并集、tech_stack 规范化）
"""
import pytest

from backend.app.services import resume_parser

SAMPLE_TEXT = """张三，男，1999年出生
邮箱：zhangsan@example.com，电话：13812345678
本科毕业于北京大学，计算机科学与技术专业，3年工作经验
熟悉 Python开发、FastAPI、MySQL、Redis，了解机器学习与RAG
项目：开发内部数据报表系统，负责后端 API 与数据库设计，支撑日均5w请求
"""


def _patch_chat_json(monkeypatch, result=None, error=None):
    def fake(*args, **kwargs):
        if error is not None:
            raise error
        return result

    monkeypatch.setattr(resume_parser.llm, "chat_json", fake)


# ============ 规则提取 ============

def test_rule_extract_contact_and_degree():
    r = resume_parser._rule_extract(SAMPLE_TEXT)
    assert r["email"] == "zhangsan@example.com"
    assert r["phone"] == "13812345678"
    assert r["degree"] == "本科"
    assert r["years_experience"] == 3


def test_rule_extract_skills_lexicon():
    r = resume_parser._rule_extract(SAMPLE_TEXT)
    skills = r["skills"]
    # 紧贴中文的写法也能命中
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "MySQL" in skills
    assert "Redis" in skills
    assert "机器学习" in skills
    assert "RAG" in skills


def test_skill_boundary_no_java_from_javascript():
    # JavaScript 不应命中 Java；gitlab 不应额外产生 git 之外的名字
    r = resume_parser._rule_extract("精通 JavaScript 和 GitLab，偶尔写 Java")
    assert "JavaScript" in r["skills"]
    assert "Java" in r["skills"]          # 文本里确有 Java
    assert r["skills"].count("Java") == 1

    r2 = resume_parser._rule_extract("使用 JavaScript 处理前端交互逻辑")
    assert "JavaScript" in r2["skills"]
    assert "Java" not in r2["skills"]


def test_rule_education_school_cleaning():
    edu = resume_parser._rule_education("本科毕业于北京大学，计算机科学与技术专业")
    assert edu and edu[0]["school"] == "北京大学"
    assert edu[0]["major"] == "计算机科学与技术"


def test_rule_years_variants():
    for text, expect in [
        ("3年工作经验", 3),
        ("2年以上开发经验", 2),
        ("2年相关开发经验", 2),
        ("5年左右后端开发经验", 5),
        ("2024年6月毕业，无相关经验", 0),  # 不应误抓"年"后的其他数字
    ]:
        assert resume_parser._rule_years(text) == expect, text


def test_rule_education_ignores_long_lines():
    # 超长行（项目描述）不应被误判成教育经历
    long_line = "在项目中负责" + "详细" * 30 + "的系统开发与维护工作"
    assert resume_parser._rule_education(long_line) == []


# ============ 降级路径 ============

def test_parse_resume_degrades_on_llm_error(monkeypatch):
    _patch_chat_json(monkeypatch, error=RuntimeError("network down"))
    result = resume_parser.parse_resume(SAMPLE_TEXT)
    assert result["rule_only"] is True
    assert result["email"] == "zhangsan@example.com"
    assert result["phone"] == "13812345678"
    assert "Python" in result["skills"]


def test_parse_resume_degrades_on_garbage_llm(monkeypatch):
    # LLM 返回非 dict（如数组），merge 必须兜住不抛异常
    _patch_chat_json(monkeypatch, result=[1, 2, 3])
    result = resume_parser.parse_resume(SAMPLE_TEXT)
    assert result["rule_only"] is True


def test_parse_resume_empty_text():
    result = resume_parser.parse_resume("")
    assert result["rule_only"] is True
    assert result["skills"] == []


def test_parse_resume_whitespace_only():
    assert resume_parser.parse_resume("   \n  ")["rule_only"] is True


# ============ 规则 + LLM 融合 ============

def test_parse_resume_merges_llm_and_rule(monkeypatch):
    llm_out = {
        "name": "李四",
        "email": "wrong@fake.com",  # 规则已抓到正确邮箱，应被规则覆盖
        "skills": ["Docker", "Python"],
        "projects": [
            {
                "name": "报表系统",
                "role": "后端开发",
                "description": "支撑日均5w请求",
                "tech_stack": "FastAPI, Redis",  # 字符串应被规范化为 list
                "achievements": "响应时间降低 50%",
            }
        ],
        "summary": "3 年后端经验",
    }
    _patch_chat_json(monkeypatch, result=llm_out)
    result = resume_parser.parse_resume(SAMPLE_TEXT)

    assert result["rule_only"] is False
    assert result["name"] == "李四"
    # 规则字段优先
    assert result["email"] == "zhangsan@example.com"
    assert result["phone"] == "13812345678"
    # 技能并集、保序去重（规则技能在前，LLM 补充在后）
    assert result["skills"][0] == "Python"
    assert set(result["skills"]) >= {"Python", "FastAPI", "MySQL", "Redis", "Docker"}
    # tech_stack 规范化
    assert result["projects"][0]["tech_stack"] == ["FastAPI", "Redis"]
    # 经验年限
    assert result["years_experience"] == 3


def test_parse_resume_llm_without_required_keys(monkeypatch):
    # LLM 只给了 name，其余关键结构字段需由规则兜底
    _patch_chat_json(monkeypatch, result={"name": "王五"})
    result = resume_parser.parse_resume(SAMPLE_TEXT)
    assert result["name"] == "王五"
    assert result["skills"]  # 规则技能仍保留
    assert result["email"] == "zhangsan@example.com"
