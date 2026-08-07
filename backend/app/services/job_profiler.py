"""岗位画像模块（成员A：任务1）。

职责：从岗位 JD（title/description/requirements/skills）抽取能力维度、核心技能、考察重点，
为面试 Agent 的选题与追问提供依据。
"""
from __future__ import annotations

import logging
from typing import Any

from ..utils import llm

_JOB_PROFILE_SYSTEM = """你是资深招聘分析师。请基于岗位信息生成"岗位画像"，以 JSON 返回：
{
  "title": "岗位名称",
  "core_skills": ["核心技能数组"],
  "capability_dimensions": [{"name": "能力维度", "weight": 权重0-1, "description": "考察什么"}],
  "interview_focus": ["面试应重点考察的点数组"],
  "suggested_rounds": ["建议面试环节数组，如 自我介绍/项目深挖/专业能力/行为面试/反问"]
}
只输出 JSON。"""


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
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": _JOB_PROFILE_SYSTEM},
                {"role": "user", "content": text[:4000]},
            ]
        )
        return data
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("岗位画像降级为规则模式: %s", exc)
        skills = [s.strip() for s in (job.get("skills") or "").split(",") if s.strip()]
        return {
            "title": job.get("title", ""),
            "core_skills": skills,
            "capability_dimensions": [{"name": "专业能力", "weight": 0.5, "description": job.get("requirements", "")}],
            "interview_focus": [job.get("requirements", "")],
            "suggested_rounds": ["self_intro", "project", "technical", "behavioral", "reverse"],
        }
