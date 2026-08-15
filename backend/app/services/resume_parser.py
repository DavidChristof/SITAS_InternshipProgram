"""简历解析模块（成员A）。

职责：从简历文本抽取教育经历、项目经历、技能关键词、联系方式、经验年限等结构化画像。
策略：规则提取先行（正则抓邮箱/手机/学历/经验年限/技能词库/学校），再 LLM 补全并核实；
      LLM 失败时降级为纯规则结果，保证接口不抛异常（降级优先铁律）。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..utils import llm

logger = logging.getLogger(__name__)

# ============ 规则提取 ============

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_YEARS_RE = re.compile(r"(\d{1,2})\s*年(?:(?:以上|多|左右|工作|开发|实习|相关|后端|前端|算法|数据|研发)\s*){0,3}?经验")
_SCHOOL_RE = re.compile(r"[一-龥]{2,20}?(?:大学|学院)")

_DEGREE_KEYWORDS = ["博士", "硕士", "本科", "大专", "学士"]

_MAJOR_KEYWORDS = [
    "计算机科学与技术", "软件工程", "人工智能", "电子信息工程", "通信工程",
    "数据科学与大数据技术", "信息管理与信息系统", "网络工程", "数学与应用数学",
    "统计学", "工商管理", "金融学", "自动化", "机械设计制造及其自动化",
    "土木工程", "数字媒体技术", "英语", "法学",
]

# 技能词库：(正则串, 规范化名称)。
# ASCII 词用 (?<![A-Za-z0-9])...(?![A-Za-z]) 做边界：支持"Python开发"这类紧贴中文的写法，
# 同时避免 "Java" 误配 "JavaScript"、"git" 误配 "gitlab"。
_SKILL_RAW: list[tuple[str, str]] = [
    # ---- 编程语言 ----
    (r"(?<![A-Za-z0-9])python(?![A-Za-z])", "Python"),
    (r"(?<![A-Za-z0-9])java(?![A-Za-z])", "Java"),
    (r"(?<![A-Za-z0-9])c\+\+(?![A-Za-z0-9])", "C++"),
    (r"(?<![A-Za-z0-9])c#(?![A-Za-z0-9])", "C#"),
    (r"(?<![A-Za-z0-9])golang(?![A-Za-z])", "Go"),
    (r"(?<![A-Za-z0-9])go(?![A-Za-z])", "Go"),
    (r"(?<![A-Za-z0-9])rust(?![A-Za-z])", "Rust"),
    (r"(?<![A-Za-z0-9])scala(?![A-Za-z])", "Scala"),
    (r"(?<![A-Za-z0-9])kotlin(?![A-Za-z])", "Kotlin"),
    (r"(?<![A-Za-z0-9])php(?![A-Za-z])", "PHP"),
    (r"(?<![A-Za-z0-9])ruby(?![A-Za-z])", "Ruby"),
    (r"(?<![A-Za-z0-9])typescript(?![A-Za-z])", "TypeScript"),
    (r"(?<![A-Za-z0-9])javascript(?![A-Za-z])", "JavaScript"),
    (r"(?<![A-Za-z0-9])html5?(?![A-Za-z0-9])", "HTML"),
    (r"(?<![A-Za-z0-9])css3?(?![A-Za-z0-9])", "CSS"),
    (r"(?<![A-Za-z0-9])sql(?![A-Za-z])", "SQL"),
    (r"(?<![A-Za-z0-9])matlab(?![A-Za-z])", "MATLAB"),
    # ---- 后端框架 / 语言生态 ----
    (r"(?<![A-Za-z0-9])fastapi(?![A-Za-z])", "FastAPI"),
    (r"(?<![A-Za-z0-9])flask(?![A-Za-z])", "Flask"),
    (r"(?<![A-Za-z0-9])django(?![A-Za-z])", "Django"),
    (r"(?<![A-Za-z0-9])spring\s*boot(?![A-Za-z])", "Spring Boot"),
    (r"(?<![A-Za-z0-9])spring\s*cloud(?![A-Za-z])", "Spring Cloud"),
    (r"(?<![A-Za-z0-9])spring(?!\s*(?:boot|cloud))(?![A-Za-z])", "Spring"),
    (r"(?<![A-Za-z0-9])mybatis(?![A-Za-z])", "MyBatis"),
    (r"(?<![A-Za-z0-9])hibernate(?![A-Za-z])", "Hibernate"),
    (r"(?<![A-Za-z0-9])node\.js(?![A-Za-z])", "Node.js"),
    (r"(?<![A-Za-z0-9])express(?![A-Za-z])", "Express"),
    (r"(?<![A-Za-z0-9])pytest(?![A-Za-z])", "pytest"),
    (r"(?<![A-Za-z0-9])requests(?![A-Za-z])", "requests"),
    (r"(?<![A-Za-z0-9])celery(?![A-Za-z])", "Celery"),
    # ---- 前端 ----
    (r"(?<![A-Za-z0-9])react(?![A-Za-z])", "React"),
    (r"(?<![A-Za-z0-9])vue(?![A-Za-z])", "Vue"),
    (r"(?<![A-Za-z0-9])angular(?![A-Za-z])", "Angular"),
    (r"(?<![A-Za-z0-9])jquery(?![A-Za-z])", "jQuery"),
    (r"(?<![A-Za-z0-9])bootstrap(?![A-Za-z])", "Bootstrap"),
    # ---- 数据库 ----
    (r"(?<![A-Za-z0-9])mysql(?![A-Za-z])", "MySQL"),
    (r"(?<![A-Za-z0-9])postgresql(?![A-Za-z])", "PostgreSQL"),
    (r"(?<![A-Za-z0-9])postgres(?![A-Za-z])", "PostgreSQL"),
    (r"(?<![A-Za-z0-9])oracle(?![A-Za-z])", "Oracle"),
    (r"(?<![A-Za-z0-9])sqlite(?![A-Za-z])", "SQLite"),
    (r"(?<![A-Za-z0-9])sql\s*server(?![A-Za-z])", "SQL Server"),
    (r"(?<![A-Za-z0-9])redis(?![A-Za-z])", "Redis"),
    (r"(?<![A-Za-z0-9])mongodb(?![A-Za-z])", "MongoDB"),
    (r"(?<![A-Za-z0-9])elasticsearch(?![A-Za-z])", "Elasticsearch"),
    (r"(?<![A-Za-z0-9])clickhouse(?![A-Za-z])", "ClickHouse"),
    (r"(?<![A-Za-z0-9])hive(?![A-Za-z])", "Hive"),
    (r"(?<![A-Za-z0-9])hbase(?![A-Za-z])", "HBase"),
    # ---- 大数据 / AI ----
    (r"(?<![A-Za-z0-9])spark(?![A-Za-z])", "Spark"),
    (r"(?<![A-Za-z0-9])hadoop(?![A-Za-z])", "Hadoop"),
    (r"(?<![A-Za-z0-9])kafka(?![A-Za-z])", "Kafka"),
    (r"(?<![A-Za-z0-9])flink(?![A-Za-z])", "Flink"),
    (r"(?<![A-Za-z0-9])tensorflow(?![A-Za-z])", "TensorFlow"),
    (r"(?<![A-Za-z0-9])pytorch(?![A-Za-z])", "PyTorch"),
    (r"(?<![A-Za-z0-9])keras(?![A-Za-z])", "Keras"),
    (r"(?<![A-Za-z0-9])opencv(?![A-Za-z])", "OpenCV"),
    (r"(?<![A-Za-z0-9])scikit(?![A-Za-z])learn", "scikit-learn"),
    (r"(?<![A-Za-z0-9])pandas(?![A-Za-z])", "pandas"),
    (r"(?<![A-Za-z0-9])numpy(?![A-Za-z])", "NumPy"),
    (r"(?<![A-Za-z0-9])langchain(?![A-Za-z])", "LangChain"),
    (r"(?<![A-Za-z0-9])llm(?![A-Za-z])", "LLM"),
    (r"(?<![A-Za-z0-9])rag(?![A-Za-z])", "RAG"),
    (r"机器学习", "机器学习"),
    (r"深度学习", "深度学习"),
    (r"自然语言处理", "自然语言处理"),
    (r"大模型", "大模型"),
    (r"数据挖掘", "数据挖掘"),
    # ---- 运维 / 云 / 工程 ----
    (r"(?<![A-Za-z0-9])docker(?![A-Za-z])", "Docker"),
    (r"(?<![A-Za-z0-9])kubernetes(?![A-Za-z])", "Kubernetes"),
    (r"(?<![A-Za-z0-9])k8s(?![A-Za-z])", "Kubernetes"),
    (r"(?<![A-Za-z0-9])nginx(?![A-Za-z])", "Nginx"),
    (r"(?<![A-Za-z0-9])jenkins(?![A-Za-z])", "Jenkins"),
    (r"(?<![A-Za-z0-9])gitlab(?![A-Za-z])", "Git"),
    (r"(?<![A-Za-z0-9])gitee(?![A-Za-z])", "Git"),
    (r"(?<![A-Za-z0-9])github(?![A-Za-z])", "Git"),
    (r"(?<![A-Za-z0-9])git(?![A-Za-z])", "Git"),
    (r"(?<![A-Za-z0-9])linux(?![A-Za-z])", "Linux"),
    (r"(?<![A-Za-z0-9])aws(?![A-Za-z])", "AWS"),
    (r"阿里云", "阿里云"),
    (r"腾讯云", "腾讯云"),
    (r"微服务", "微服务"),
    (r"分布式", "分布式"),
    (r"高并发", "高并发"),
    (r"多线程", "多线程"),
    (r"单元测试", "单元测试"),
    (r"爬虫", "爬虫"),
    (r"(?<![A-Za-z0-9])restful(?![A-Za-z])", "RESTful"),
    (r"(?<![A-Za-z0-9])websocket(?![A-Za-z])", "WebSocket"),
]

# 生成模式匹配对象
_SKILL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(pat, re.IGNORECASE), name) for pat, name in _SKILL_RAW
]

_SUMMARY_TRIGGERS = ("经验", "负责", "熟悉", "精通", "掌握", "开发", "参与", "毕业于", "求职", "意向")
_SCHOOL_PREFIXES = ("毕业于", "现就读于", "就读于", "于", "在", "本科", "硕士", "博士", "大专", "学士", "在校")


def _dedupe(items: list[str]) -> list[str]:
    """保序去重。"""
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def _extract_skills(text: str) -> list[str]:
    return _dedupe([name for pat, name in _SKILL_PATTERNS if pat.search(text)])


def _clean_school(raw: str) -> str:
    """循环剥掉"本科/毕业于/于"等前缀，直到没有前缀可剥（避免剥完本科仍残留"毕业于"）。"""
    changed = True
    while changed and raw:
        changed = False
        for prefix in _SCHOOL_PREFIXES:
            if raw.startswith(prefix):
                raw = raw[len(prefix):]
                changed = True
    return raw


def _rule_education(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > 60:
            continue
        degree = next((d for d in _DEGREE_KEYWORDS if d in line), "")
        school = _SCHOOL_RE.search(line)
        major = next((m for m in _MAJOR_KEYWORDS if m in line), "")
        if degree or school or major:
            rows.append(
                {
                    "school": _clean_school(school.group(0)) if school else "",
                    "degree": degree,
                    "major": major,
                    "years": line[:40],
                }
            )
    return rows[:5]


def _rule_years(text: str) -> int:
    m = _YEARS_RE.search(text)
    return int(m.group(1)) if m else 0


def _rule_summary(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if 8 <= len(line) <= 80 and any(t in line for t in _SUMMARY_TRIGGERS):
            return line
    return ""


def _rule_extract(text: str) -> dict[str, Any]:
    """纯规则提取的兜底画像。"""
    degree = next((d for d in _DEGREE_KEYWORDS if d in text), "")
    return {
        "name": "",
        "email": (_EMAIL_RE.findall(text) or [""])[0],
        "phone": (_PHONE_RE.findall(text) or [""])[0],
        "degree": degree,
        "years_experience": _rule_years(text),
        "education": _rule_education(text),
        "projects": [],  # 规则难以可靠抽取项目，交给 LLM 补全
        "skills": _extract_skills(text),
        "internships": [],
        "summary": _rule_summary(text),
        "rule_only": True,
    }


# ============ LLM 解析 ============
_RESUME_PARSE_SYSTEM = """你是资深简历解析助手。请从候选人简历文本中抽取以下结构化字段，只输出 JSON，不要任何解释：
{
  "name": "姓名",
  "email": "邮箱（没有就填空字符串）",
  "phone": "手机号（没有就填空字符串）",
  "degree": "学历（博士/硕士/本科/大专/其他，没有就空字符串）",
  "years_experience": 工作经验年数（数字，没有就填 0）,
  "education": [{"school": "学校", "degree": "学历", "major": "专业", "years": "就读时间"}],
  "projects": [{"name": "项目名", "role": "担任角色", "description": "项目描述", "tech_stack": ["技术栈数组"], "achievements": "成果与量化指标"}],
  "skills": ["技能关键词数组"],
  "internships": [{"company": "公司", "position": "职位", "duration": "时长", "description": "职责描述"}],
  "summary": "一句话候选人概述"
}
注意：简历文本可能来自 PDF/docx 转换，存在排版噪声；邮件/手机/学历以原文为准；无法确定的字段留空或空数组，不要编造。"""


def _merge(rule: dict[str, Any], llm_data: dict[str, Any]) -> dict[str, Any]:
    """规则结果与 LLM 结果融合。

    确定性字段（邮箱/手机/学历/经验年限/技能）以规则为准——正则比 LLM 稳；
    结构化文本字段（项目/实习/教育/概述）以 LLM 为准，规则缺失时兜底。
    """
    out = dict(llm_data or {})
    for field in ("education", "projects", "skills", "internships", "summary"):
        out.setdefault(field, rule.get(field, [] if field != "summary" else ""))

    for field in ("email", "phone", "degree"):
        if rule.get(field):
            out[field] = rule[field]
        elif not out.get(field):
            out[field] = ""

    years = rule.get("years_experience")
    if not years:
        try:
            years = int(out.get("years_experience"))
        except (TypeError, ValueError):
            years = 0
    out["years_experience"] = years

    # 技能：规则 ∪ LLM，保序去重
    out["skills"] = _dedupe([*(rule.get("skills") or []), *(out.get("skills") or [])])

    # 项目技术栈统一规范化为 list（LLM 可能返回字符串）
    for p in out.get("projects") or []:
        ts = p.get("tech_stack")
        if isinstance(ts, str):
            p["tech_stack"] = [t for t in re.split(r"[,，、/;；+\s]+", ts) if t]
    return out


def _rule_hint(rule: dict[str, Any]) -> str:
    """把规则识别结果作为提示带给 LLM，让 LLM 与规则保持一致。"""
    parts: list[str] = []
    if rule.get("email"):
        parts.append(f"邮箱={rule['email']}")
    if rule.get("phone"):
        parts.append(f"手机={rule['phone']}")
    if rule.get("degree"):
        parts.append(f"学历={rule['degree']}")
    if rule.get("years_experience"):
        parts.append(f"经验={rule['years_experience']}年")
    if rule.get("skills"):
        parts.append(f"技能={'、'.join(rule['skills'][:10])}")
    schools = "、".join(e["school"] for e in rule.get("education") or [] if e.get("school"))
    if schools:
        parts.append(f"学校={schools}")
    return "；".join(parts)


def parse_resume(resume_text: str) -> dict[str, Any]:
    """解析简历文本，返回结构化画像。

    返回字段（供面试 Agent / 岗位画像使用）：
    name, email, phone, degree, years_experience, education[], projects[], skills[],
    internships[], summary, rule_only（True 表示降级为规则结果）
    """
    rule = _rule_extract(resume_text)
    if not resume_text or not resume_text.strip():
        return rule

    hint = _rule_hint(rule)
    user_content = resume_text[:6000]
    if hint:
        user_content += "\n\n（已用规则识别到：" + hint + "，请核对并补全其它字段）"

    messages = [
        {"role": "system", "content": _RESUME_PARSE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    try:
        data = llm.chat_json(messages)
        merged = _merge(rule, data)
        merged["rule_only"] = False
        return merged
    except Exception as exc:  # noqa: BLE001  网络/解析失败一律降级
        logger.warning("简历解析降级为规则模式: %s", exc)
        return rule
