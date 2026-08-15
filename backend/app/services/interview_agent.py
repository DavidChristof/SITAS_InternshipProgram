"""AI 面试 Agent（成员A：任务3，本项目核心）。

职责：根据岗位画像、简历画像和已有问答，自动生成问题、追问、评分与改进建议。
同时封装"面试状态控制"所需的最小接口（plan_interview / generate_followup / evaluate_answer），
面试状态机本身的持久化由成员B在 API 层实现。

全部函数要求：不抛异常；LLM 不可用时返回保守的规则结果，保证面试流程可继续。
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..rag import knowledge_base
from ..rag.prompts import (
    behavioral,
    project_deep_dive,
    reverse_qa,
    self_intro,
    technical,
)
from ..utils import llm

logger = logging.getLogger(__name__)

# 面试环节顺序与默认轮数
DEFAULT_ROUNDS: list[str] = ["self_intro", "project", "technical", "behavioral", "reverse"]


def _retrieve_evidence(query: str, top_k: int = 3) -> list[dict]:
    """从知识库检索依据（岗位JD/题库/评分标准/企业资料）。"""
    return knowledge_base.search(query, top_k=top_k)


def _as_list(value: Any) -> list[str]:
    """字符串或列表统一转为列表（容忍 LLM 把 tech_stack 返回成字符串）。"""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [v for v in re.split(r"[,，、/;；+\s]+", value) if v]
    return []


# ============ 出题 ============

def plan_interview(
    job_profile: dict[str, Any],
    resume_profile: dict[str, Any],
    categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """编排整场面试的问题序列。

    返回 list[ {round_no, category, question, expected_points, evidence} ]。
    LLM 失败时回退到题库检索，再失败回退到通用模板题。
    """
    categories = categories or DEFAULT_ROUNDS
    rounds: list[dict[str, Any]] = []
    job_title = job_profile.get("title", "该岗位")

    # 先查知识库题库，看有没有匹配岗位的题目
    bank_questions = _retrieve_evidence(f"{job_title} {job_profile.get('core_skills', [])} 面试题", top_k=5)

    for idx, cat in enumerate(categories, start=1):
        question_text, expected = _gen_question(cat, job_profile, resume_profile, bank_questions)
        rounds.append(
            {
                "round_no": idx,
                "category": cat,
                "question": question_text,
                "expected_points": expected,
                "evidence": bank_questions[:2],  # 检索依据，供前端/报告展示
            }
        )
    return rounds


def _gen_question(
    cat: str,
    job_profile: dict[str, Any],
    resume_profile: dict[str, Any],
    bank_questions: list[dict],
) -> tuple[str, str]:
    """单个环节出题。返回 (问题文本, 评分要点)。"""
    job_title = job_profile.get("title", "该岗位")
    job_req = "；".join(job_profile.get("interview_focus", []) or ["综合考察"])
    candidate = resume_profile.get("summary") or resume_profile.get("name") or "候选人"

    # 项目深挖：优先取简历第一个项目作为背景
    projects = resume_profile.get("projects") or []
    first_project = projects[0] if projects else {}
    project_brief = (
        first_project.get("description")
        or f"候选人的项目经历（{first_project.get('name', '')}）"
        or "候选人的项目经历"
    )

    # 反问环节：优先从知识库取企业资料
    company_hits = knowledge_base.search("企业资料 公司文化 发展 团队", top_k=1)
    company_brief = company_hits[0].get("content", "")[:300] if company_hits else "（暂无企业资料，可围绕岗位提问）"

    prompt_map = {
        "self_intro": (
            self_intro.SELF_INTRO_SYSTEM.format(
                job_title=job_title, candidate_summary=candidate, job_requirements=job_req
            ),
            "结构化表达、突出与岗位的匹配点",
        ),
        "project": (
            project_deep_dive.PROJECT_SYSTEM.format(
                job_title=job_title,
                project_role=first_project.get("role") or "成员",
                tech_stack=",".join(
                    _as_list(first_project.get("tech_stack"))
                    or _as_list(resume_profile.get("skills"))[:5]
                )
                or "未提供",
                project_brief=project_brief,
            ),
            "实际贡献、难点解决、量化结果",
        ),
        "technical": (
            technical.TECHNICAL_SYSTEM.format(
                job_title=job_title,
                core_skills=",".join(job_profile.get("core_skills", [])),
            ),
            "概念准确、思路清晰、完整性",
        ),
        "behavioral": (
            behavioral.BEHAVIORAL_SYSTEM.format(candidate_summary=candidate),
            "STAR 完整、反思深度",
        ),
        "reverse": (
            reverse_qa.REVERSE_SYSTEM.format(company_brief=company_brief),
            "问题质量、体现思考",
        ),
    }
    system_prompt, fallback_expected = prompt_map.get(cat, prompt_map["technical"])

    # 若知识库有"单条短题"且环节匹配，优先复用（整块多题文档不作为单题复用）
    for q in bank_questions:
        meta = q.get("meta") or {}
        content = (q.get("content") or "").strip()
        if meta.get("category") == cat and 0 < len(content) < 120 and "\n" not in content:
            return content, meta.get("expected_points", fallback_expected)

    try:
        text = llm.chat([{"role": "system", "content": system_prompt}], temperature=0.8, max_tokens=512)
        return text.strip() or f"请谈谈你对{job_title}岗位的理解。", fallback_expected
    except Exception as exc:  # noqa: BLE001
        logger.warning("出题降级: %s", exc)
        return f"请谈谈你对{job_title}岗位的理解，以及你在这方面的经验。", fallback_expected


# ============ 追问 ============

def generate_followup(
    interview_context: list[dict[str, Any]],
    job_profile: dict[str, Any],
) -> dict[str, Any]:
    """基于前几轮回答生成追问。

    interview_context: [ {round_no, category, question, answer_text} ]
    返回 {question, reason}
    """
    job_title = job_profile.get("title", "该岗位")
    history = "\n".join(
        f"第{r['round_no']}轮（{r.get('category', '')}）\n问：{r.get('question', '')}\n答：{r.get('answer_text', '')}"
        for r in interview_context
    )
    system = (
        f"你是一位{job_title}面试官。候选人的回答如下：\n{history[:4000]}\n"
        "请针对回答中不清晰、可深挖或有矛盾的地方提出 1 个追问。"
        "只输出问题本身，不要解释。"
    )
    try:
        text = llm.chat([{"role": "user", "content": system}], temperature=0.8, max_tokens=300)
        return {"question": text.strip(), "reason": "针对上一轮回答追问"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("追问降级: %s", exc)
        return {"question": "可以再展开说说你在这个部分具体做了哪些工作吗？", "reason": "降级追问"}


# ============ 评分 ============

def evaluate_answer(
    question: str,
    answer: str,
    category: str = "technical",
    expected_points: str = "",
    evidence: list[dict] | None = None,
    job_title: str = "该岗位",
) -> dict[str, Any]:
    """对单题回答评分。

    job_title 为可选参数（成员B 可从岗位信息传入，不传则用"该岗位"）。
    返回 {score: 0-100, feedback, improvement, missing_points[], evidence}
    """
    if not answer or not answer.strip():
        return {"score": 0, "feedback": "未作答", "improvement": "请给出你的回答", "missing_points": [], "evidence": evidence or []}

    prompt_map = {
        "self_intro": self_intro.SELF_INTRO_EVALUATE,
        "project": project_deep_dive.PROJECT_EVALUATE,
        "technical": technical.TECHNICAL_EVALUATE,
        "behavioral": behavioral.BEHAVIORAL_EVALUATE,
        "reverse": reverse_qa.REVERSE_EVALUATE,
    }
    template = prompt_map.get(category, prompt_map["technical"])

    # 模板只引用以下 5 个安全字段（带默认值），保证 .format() 永不抛 KeyError
    context = {
        "job_title": job_title,
        "job_requirements": expected_points or "综合考察",
        "question": question,
        "expected_points": expected_points or "",
        "answer": answer,
    }
    try:
        result = llm.chat_json([{"role": "user", "content": template.format(**context)}], temperature=0.2)
        result.setdefault("score", 60)
        result.setdefault("feedback", "")
        result.setdefault("improvement", "")
        result.setdefault("missing_points", [])
        result["evidence"] = evidence or []
        result["score"] = max(0, min(100, int(result["score"])))
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("评分降级: %s", exc)
        # 规则降级：按回答长度粗评
        length_score = min(100, max(30, len(answer) // 10))
        return {
            "score": length_score,
            "feedback": "已降级为规则评分（LLM 暂不可用）",
            "improvement": "建议回答更完整、更有条理",
            "missing_points": [],
            "evidence": evidence or [],
        }
