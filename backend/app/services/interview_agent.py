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

# 非技术环节的固定证据检索词（technical 按岗位+技能动态拼）
_CATEGORY_QUERY: dict[str, str] = {
    "self_intro": "自我介绍 常见面试题 自我认知",
    "project": "项目经历 深挖 面试问题",
    "behavioral": "行为面试 经历 冲突 团队 协作 失败",
    "reverse": "企业资料 公司文化 发展 团队",
}
# 环节英文键 -> 中文名（用于补检索，保证题库候选命中）
_CATEGORY_CN: dict[str, str] = {
    "self_intro": "自我介绍",
    "project": "项目深挖",
    "technical": "专业能力",
    "behavioral": "行为面试",
    "reverse": "反问",
}


def _retrieve_evidence(query: str, top_k: int = 3) -> list[dict]:
    """从知识库检索依据（岗位JD/题库/评分标准/企业资料）。"""
    return knowledge_base.search(query, top_k=top_k)


def _dedupe_docs(docs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for d in docs:
        if d.get("id") not in seen:
            seen.add(d.get("id"))
            out.append(d)
    return out


def _category_evidence(cat: str, job_profile: dict[str, Any]) -> list[dict]:
    """按环节检索对应的知识库依据（evidence 链）。

    技巧：查询带上环节中文名，并在结果中没有本环节题库候选时再补一次检索，
    保证"题库复用"与"证据展示"都能命中该环节的题目文档。
    """
    if cat == "technical":
        query = f"{job_profile.get('title', '')} {' '.join(job_profile.get('core_skills', []))} 面试题"
    elif cat == "reverse":
        query = _CATEGORY_QUERY["reverse"]
    else:
        query = f"{_CATEGORY_CN.get(cat, cat)} {_CATEGORY_QUERY.get(cat, '面试题')}"
    docs = _retrieve_evidence(query, top_k=5)
    if cat != "reverse" and not any((d.get("meta") or {}).get("category") == cat for d in docs):
        extra = _retrieve_evidence(f"{_CATEGORY_CN.get(cat, cat)} 面试题", top_k=3)
        docs = _dedupe_docs(docs + extra)
    return docs


def _trim_evidence(docs: list[dict], limit: int = 3) -> list[dict]:
    """裁剪证据：最多 limit 条、每条 content 截断，避免入库 payload 过大。

    注意 limit 应与 _category_evidence 的 top_k 一致，保证"证据展示"覆盖"出题依据"。
    """
    out = []
    for d in docs[:limit]:
        copy = dict(d)
        copy["content"] = (copy.get("content") or "")[:200]
        out.append(copy)
    return out


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

    for idx, cat in enumerate(categories, start=1):
        # 按环节检索对应知识库依据（evidence 链），出题与展示共用
        evidence = _category_evidence(cat, job_profile)
        question_text, expected = _gen_question(cat, job_profile, resume_profile, evidence)
        rounds.append(
            {
                "round_no": idx,
                "category": cat,
                "question": question_text,
                "expected_points": expected,
                "evidence": _trim_evidence(evidence),  # 检索依据，供前端/报告展示
            }
        )
    return rounds


def _should_reuse_bank(cat: str, resume_profile: dict[str, Any]) -> bool:
    """判断该环节是否优先复用题库题。

    优先级原则：有简历素材的环节走模板深挖（更贴合候选人），
    无素材时用题库兜底；技术面/行为面为标准化题目，始终优先复用题库。
    """
    if cat == "self_intro":
        return not (resume_profile.get("summary") or resume_profile.get("name"))
    if cat == "project":
        return not (resume_profile.get("projects"))
    return True  # technical / behavioral / reverse 之外的标准化环节


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

    # 反问环节：优先从传入的企业资料证据里取公司简介（bank_questions 对 reverse 环节即企业资料）
    company_brief = "（暂无企业资料，可围绕岗位提问）"
    for q in bank_questions:
        if q.get("source") == "企业资料" and q.get("content"):
            company_brief = q["content"][:300]
            break

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

    # 若知识库有"单条短题"且环节匹配，优先复用（整块多题文档不作为单题复用）。
    # 注意：反问环节的题属于候选人提问，不应作为面试官提问复用；有简历素材的
    # 自介/项目环节走模板深挖（见 _should_reuse_bank）。
    if cat != "reverse" and _should_reuse_bank(cat, resume_profile):
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

_FOLLOWUP_SYSTEM = """你是{job_title}面试官，正在追问候选人。基于以下面试问答记录，提出 1 个有价值的追问。
追问要针对回答中：表述不清、可以深挖、前后矛盾、缺少量化证据的地方；若回答过短或太笼统，则引导候选人展开。
只输出 JSON：
{{
  "question": "追问问题（1-2 句）",
  "reason": "追问原因，指出是基于候选人回答中的什么信息"
}}"""

_QUANT_RE = re.compile(r"[0-9一二三四五六七八九十]+|[万千百亿倍%]+|提升|降低|减少|增加|耗时|秒|人|次|行")


def _rule_followup(interview_context: list[dict[str, Any]]) -> dict[str, Any]:
    """规则降级追问：根据最后一轮回答质量给保守但合理的追问。"""
    last = interview_context[-1] if interview_context else {}
    answer = (last.get("answer_text") or "").strip()
    if not answer:
        return {
            "question": "刚才这个问题你还没回答，可以再展开说说你的想法吗？",
            "reason": "已降级为规则追问（LLM 暂不可用）：上一轮未作答",
        }
    if len(answer) < 30:
        return {
            "question": "可以再展开讲讲你在这个部分具体做了哪些工作、遇到了什么难点吗？",
            "reason": "已降级为规则追问（LLM 暂不可用）：回答过短，引导候选人展开",
        }
    if not _QUANT_RE.search(answer):
        return {
            "question": "你提到的情况能给出一些具体的数据或结果吗？比如耗时、性能或效果上的变化。",
            "reason": "已降级为规则追问（LLM 暂不可用）：回答缺少量化结果",
        }
    return {
        "question": "可以再深挖一下，当时为什么选择这个方案？有没有考虑过其他方案？",
        "reason": "已降级为规则追问（LLM 暂不可用）",
    }


def generate_followup(
    interview_context: list[dict[str, Any]],
    job_profile: dict[str, Any],
) -> dict[str, Any]:
    """基于前几轮回答生成追问。

    interview_context: [ {round_no, category, question, answer_text} ]
    返回 {question, reason}；LLM 失败/返回脏数据时按最后一轮回答质量做规则降级。
    """
    job_title = job_profile.get("title", "该岗位")
    history = "\n".join(
        f"第{r['round_no']}轮（{r.get('category', '')}）\n问：{r.get('question', '')}\n答：{r.get('answer_text', '')}"
        for r in interview_context
    )
    system = _FOLLOWUP_SYSTEM.format(job_title=job_title) + "\n\n面试记录：\n" + (history[:4000] or "（暂无记录）")
    try:
        data = llm.chat_json([{"role": "user", "content": system}], temperature=0.7, max_tokens=400)
        if not isinstance(data, dict):
            raise ValueError(f"LLM 返回非字典: {type(data).__name__}")
        question = (data.get("question") or "").strip()
        reason = (data.get("reason") or "").strip()
        if not question:
            raise ValueError("LLM 未返回追问问题")
        return {"question": question, "reason": reason or "针对上一轮回答追问"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("追问降级: %s", exc)
        return _rule_followup(interview_context)


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
        # 归一化 missing_points：LLM 偶尔返回字符串或 None
        mp = result.get("missing_points") or []
        result["missing_points"] = mp if isinstance(mp, list) else [mp]
        result["evidence"] = evidence or []
        result["score"] = max(0, min(100, int(result["score"])))
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("评分降级: %s", exc)
        score, missing = _rule_score(answer, expected_points)
        return {
            "score": score,
            "feedback": "已降级为规则评分（LLM 暂不可用）",
            "improvement": "建议回答更完整、更有条理，尽量覆盖评分要点",
            "missing_points": missing,
            "evidence": evidence or [],
        }


def _rule_score(answer: str, expected_points: str) -> tuple[int, list[str]]:
    """规则降级评分：评分要点命中率（60 分）+ 回答完整度（40 分）。

    用于 LLM 不可用时的保守评分，保证演示/无 key 场景仍有合理区分度。
    """
    text = (answer or "").strip()
    points = [p.strip() for p in re.split(r"[,，、/;；+\s]+", expected_points or "") if p.strip()]
    missing = [p for p in points if p and p not in text]
    hit = len(points) - len(missing)
    points_score = round(60 * hit / len(points)) if points else 30

    if len(text) < 20:
        complete = 10
    elif len(text) < 40:
        complete = 25
    else:
        complete = 40

    return max(5, min(95, points_score + complete)), missing
