"""岗位画像模块（成员A：任务1）。

职责：从岗位 JD（title/description/requirements/skills）抽取能力维度、核心技能、考察重点，
为面试 Agent 的选题与追问提供依据。
策略：规则提取先行（技能词库 + 维度关键词规则），LLM 补全并核实；失败降级为纯规则结果。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..utils import llm
from .resume_parser import _dedupe, _extract_skills  # 复用技能词库与去重

logger = logging.getLogger(__name__)

_JOB_PROFILE_SYSTEM = """你是资深招聘分析师。请基于岗位信息生成"岗位画像"，只输出 JSON：
{
  "title": "岗位名称",
  "core_skills": ["核心技能数组"],
  "capability_dimensions": [{"name": "能力维度", "weight": 0-1 权重, "description": "考察什么"}],
  "interview_focus": ["面试应重点考察的点数组"],
  "suggested_rounds": ["建议面试环节，用英文键：self_intro/project/technical/behavioral/reverse"]
}
要求：
- core_skills 从岗位 JD 提取，至少 3 个、最多 8 个
- capability_dimensions 3-5 个，权重和为 1
- interview_focus 3-5 条具体可考察的要点
- suggested_rounds 必须用英文环节键
只输出 JSON，不要任何解释。"""

# 中文环节标签 -> 英文键（防御：LLM 偶尔仍返回中文）
_ROUND_LABEL_MAP = {
    "自我介绍": "self_intro", "自我认知": "self_intro",
    "项目深挖": "project", "项目经历": "project",
    "专业能力": "technical", "技术": "technical", "专业技能": "technical",
    "行为面试": "behavioral", "行为": "behavioral",
    "反问": "reverse", "提问": "reverse",
}


def _normalize_rounds(rounds: list[str] | None) -> list[str]:
    if not rounds:
        return []
    return [_ROUND_LABEL_MAP.get(r, r) for r in rounds]

# 能力维度关键词 -> (维度名, 基础权重)。命中多条取命中的再归一化权重。
_DIMENSION_RULES: list[tuple[tuple[str, ...], str, float]] = [
    (("编程", "开发", "框架", "语言", "代码", "后端", "前端", "算法", "数据结构", "测试", "数据库"), "专业能力", 0.45),
    (("项目", "经历", "经验", "负责", "落地", "实战"), "项目实践", 0.25),
    (("沟通", "协作", "团队", "跨部门", "组织", "协调"), "沟通协作", 0.12),
    (("学习", "成长", "钻研", "新技术", "自驱", "持续"), "学习成长", 0.10),
    (("抗压", "责任心", "主动性", "执行力", "自律", "细致"), "职业素养", 0.08),
]

_FALLBACK_DIMENSIONS: list[dict[str, Any]] = [
    {"name": "专业能力", "weight": 0.5, "description": "岗位所需专业知识和技能"},
    {"name": "项目实践", "weight": 0.3, "description": "实际项目落地能力"},
    {"name": "综合素质", "weight": 0.2, "description": "沟通协作与学习能力"},
]

_FOCUS_TRIGGERS = ("熟悉", "掌握", "负责", "要求", "有", "参与", "经验", "了解", "具备")


def _rule_focus(text: str) -> list[str]:
    """从 JD 文本切出 3-4 条考察重点（按分隔符切分并过滤无意义片段）。"""
    parts: list[str] = []
    for seg in re.split(r"[。；;\n，,、]", text):
        seg = seg.strip()
        if 4 <= len(seg) <= 30 and any(k in seg for k in _FOCUS_TRIGGERS):
            parts.append(seg)
    return parts[:4]


def _rule_profile(text: str, title: str) -> dict[str, Any]:
    """纯规则岗位画像（LLM 不可用时）。"""
    skills = _extract_skills(text)
    dims: list[dict[str, Any]] = []
    for keywords, name, base in _DIMENSION_RULES:
        if any(k in text for k in keywords):
            dims.append({"name": name, "weight": base, "description": f"重点考察{name}"})
    if not dims:
        dims = [dict(d) for d in _FALLBACK_DIMENSIONS]
    total = sum(d["weight"] for d in dims)
    for d in dims:
        d["weight"] = round(d["weight"] / total, 2)
    return {
        "title": title,
        "core_skills": skills or [],
        "capability_dimensions": dims,
        "interview_focus": _rule_focus(text) or ["综合考察"],
        "suggested_rounds": ["self_intro", "project", "technical", "behavioral", "reverse"],
    }


def _merge_profile(rule: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """规则结果与 LLM 结果融合。技能以词库检测为准（并集），维度/要点以 LLM 为准（缺失则规则兜底）。"""
    return {
        "title": data.get("title") or rule["title"],
        "core_skills": _dedupe([*rule["core_skills"], *[str(s) for s in (data.get("core_skills") or [])]]),
        "capability_dimensions": data.get("capability_dimensions") or rule["capability_dimensions"],
        "interview_focus": data.get("interview_focus") or rule["interview_focus"],
        "suggested_rounds": _normalize_rounds(data.get("suggested_rounds")) or rule["suggested_rounds"],
    }


def build_job_profile(job: Any) -> dict[str, Any]:
    """从岗位对象生成岗位画像。

    job 可为 ORM 对象或 dict，要求包含 title / description / requirements / skills。
    返回：title, core_skills[], capability_dimensions[], interview_focus[], suggested_rounds[]
    """
    if hasattr(job, "title"):  # ORM 对象
        job = {
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
            "skills": job.skills,
        }
    text = (
        f"岗位名称：{job.get('title', '')}\n"
        f"岗位JD：{job.get('description', '')}\n"
        f"任职要求：{job.get('requirements', '')}\n"
        f"技能关键词：{job.get('skills', '')}"
    )
    rule = _rule_profile(text, job.get("title", ""))
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": _JOB_PROFILE_SYSTEM},
                {"role": "user", "content": text[:4000]},
            ]
        )
        if not isinstance(data, dict):
            raise ValueError(f"LLM 返回非字典: {type(data).__name__}")
        return _merge_profile(rule, data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("岗位画像降级为规则模式: %s", exc)
        return rule
