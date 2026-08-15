"""岗位画像规则提取 + 规则/LLM 融合 + 降级测试（成员A）。

验证：
1. 规则模式能从 JD 文本提取技能（复用词库）、能力维度（权重和为 1）、考察重点
2. LLM 失败/返回脏数据时降级为规则结果（不抛异常、字段齐全）
3. LLM 成功时正确融合（技能并集、缺失字段规则兜底）
4. 兼容 ORM 对象与 dict 两种入参
"""
import pytest

from backend.app.services import job_profiler

JD_TEXT = {
    "title": "Python 后端开发工程师",
    "description": "负责公司内部系统的后端开发，要求熟悉 Python、FastAPI、MySQL，有实际项目经验，具备良好的沟通协作能力。",
    "requirements": "熟悉 Python/FastAPI/数据库；有 2 年以上项目经验；责任心强，善于团队协作",
    "skills": "Python,FastAPI,Redis",
}


def _patch_chat_json(monkeypatch, result=None, error=None):
    def fake(*args, **kwargs):
        if error is not None:
            raise error
        return result

    monkeypatch.setattr(job_profiler.llm, "chat_json", fake)


# ============ 规则模式 ============

def test_rule_profile_skills_and_dimensions():
    text = (
        "岗位名称：Python 后端开发工程师\n岗位JD：负责后端开发\n"
        "任职要求：熟悉 Python、FastAPI、MySQL，有项目经验，沟通协作能力强"
    )
    r = job_profiler._rule_profile(text, "Python 后端开发工程师")
    # 技能词库命中
    assert {"Python", "FastAPI", "MySQL"} <= set(r["core_skills"])
    # 能力维度关键词命中
    names = [d["name"] for d in r["capability_dimensions"]]
    assert "专业能力" in names
    assert "项目实践" in names
    assert "沟通协作" in names
    # 权重和为 1
    assert abs(sum(d["weight"] for d in r["capability_dimensions"]) - 1.0) < 1e-6
    # 环节完整
    assert r["suggested_rounds"] == ["self_intro", "project", "technical", "behavioral", "reverse"]


def test_rule_profile_fallback_dimensions():
    # 无任何维度关键词命中时给默认维度
    r = job_profiler._rule_profile("岗位JD：这是一个没有关键词的岗位描述。", "测试岗")
    assert r["capability_dimensions"]
    assert abs(sum(d["weight"] for d in r["capability_dimensions"]) - 1.0) < 1e-6


def test_rule_focus_splits_requirements():
    focus = job_profiler._rule_focus("熟悉 Python/FastAPI；有项目经验；责任心强")
    assert focus  # 应切出有意义片段
    assert all(4 <= len(f) <= 30 for f in focus)


# ============ 降级 ============

def test_build_job_profile_degrades_on_llm_error(monkeypatch):
    _patch_chat_json(monkeypatch, error=RuntimeError("network down"))
    r = job_profiler.build_job_profile(JD_TEXT)
    assert set(r) == {"title", "core_skills", "capability_dimensions", "interview_focus", "suggested_rounds"}
    assert r["title"] == "Python 后端开发工程师"
    assert "Python" in r["core_skills"]


def test_build_job_profile_degrades_on_garbage(monkeypatch):
    _patch_chat_json(monkeypatch, result=["not", "a", "dict"])
    r = job_profiler.build_job_profile(JD_TEXT)
    assert "Python" in r["core_skills"]


# ============ 融合 ============

def test_build_job_profile_merges_llm(monkeypatch):
    llm_out = {
        "title": "Python 后端开发工程师",
        "core_skills": ["Python"],  # 规则词库还有 FastAPI/MySQL/Redis，应并集
        "capability_dimensions": [{"name": "专业能力", "weight": 1.0, "description": "后端"}],
        "interview_focus": ["数据库设计"],
        "suggested_rounds": ["technical"],
    }
    _patch_chat_json(monkeypatch, result=llm_out)
    r = job_profiler.build_job_profile(JD_TEXT)
    assert {"Python", "FastAPI", "MySQL"} <= set(r["core_skills"])
    assert r["capability_dimensions"] == llm_out["capability_dimensions"]
    assert r["interview_focus"] == ["数据库设计"]
    assert r["suggested_rounds"] == ["technical"]


def test_suggested_rounds_chinese_labels_normalized(monkeypatch):
    # LLM 返回中文环节标签，应归一化为英文键
    _patch_chat_json(
        monkeypatch,
        result={"suggested_rounds": ["自我介绍", "项目深挖", "专业能力", "行为面试", "反问"]},
    )
    r = job_profiler.build_job_profile(JD_TEXT)
    assert r["suggested_rounds"] == ["self_intro", "project", "technical", "behavioral", "reverse"]


def test_build_job_profile_llm_missing_fields_falls_back_to_rule(monkeypatch):
    # LLM 只给 title，其余字段由规则兜底
    _patch_chat_json(monkeypatch, result={"title": "Python 后端开发工程师"})
    r = job_profiler.build_job_profile(JD_TEXT)
    assert r["core_skills"]  # 规则兜底
    assert r["capability_dimensions"]


def test_build_job_profile_accepts_orm_object(monkeypatch):
    class _Job:
        title = "前端开发"
        description = "负责 Web 前端页面开发"
        requirements = "熟悉 Vue、JavaScript"
        skills = "Vue,JavaScript"

    _patch_chat_json(monkeypatch, error=RuntimeError("no key"))
    r = job_profiler.build_job_profile(_Job())
    assert r["title"] == "前端开发"
    assert "Vue" in r["core_skills"] or "JavaScript" in r["core_skills"]
