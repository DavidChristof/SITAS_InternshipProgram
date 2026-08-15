"""面试报告生成模块（成员A）。

职责：聚合候选人信息、逐题问答、维度得分，用 LLM 生成总体评价与改进建议，
输出含雷达图数据（radar_scores）、优缺点、录用建议的完整结构化报告。
LLM 不可用时按维度得分生成规则版评语，保证演示/无 key 场景报告仍完整。
"""
from __future__ import annotations

import datetime as _dt
import logging
from typing import Any

from . import scoring
from ..utils import llm

logger = logging.getLogger(__name__)

_REPORT_SYSTEM = """你是资深 HR 专家。请基于以下面试数据撰写一份结构化人才评估报告，只输出 JSON：
{
  "overall_comment": "总体评价（3-5句，结合维度得分与具体答题表现）",
  "strengths": ["优势数组，至少2条，来自高分维度或具体表现"],
  "weaknesses": ["不足数组，至少2条，来自低分维度或具体表现"],
  "suggestions": ["针对性改进建议数组，至少2条"],
  "hire_recommendation": "建议录用 / 建议培养 / 暂不匹配"
}
"""


def _rule_report(agg: dict[str, Any]) -> dict[str, Any]:
    """规则版评语（LLM 不可用）：按维度得分生成优缺点与录用建议。"""
    dims = agg["dimension_scores"]
    strengths = [f"{d} 表现较好（{s} 分）" for d, s in dims.items() if s >= 80]
    weaknesses = [f"{d} 有待加强（{s} 分）" for d, s in dims.items() if s < 60]
    suggestions = ["针对薄弱维度补充系统学习与项目实践", "回答时注重结构化表达与量化结果"]

    total = agg["total_score"]
    if total >= 80:
        rec = "建议录用"
    elif total >= 60:
        rec = "建议培养"
    else:
        rec = "暂不匹配"
    overall = (
        f"候选人本次面试总分 {total}（{scoring.level_from_score(total)}级），"
        f"整体表现{'良好' if total >= 70 else '一般，建议针对性提升'}。"
    )
    return {
        "overall_comment": overall,
        "strengths": strengths or ["暂无显著优势维度"],
        "weaknesses": weaknesses or ["暂无明显短板，需结合具体答题深入评估"],
        "suggestions": suggestions,
        "hire_recommendation": rec,
    }


_AI_DEFAULTS: dict[str, Any] = {
    "overall_comment": "",
    "strengths": [],
    "weaknesses": [],
    "suggestions": [],
    "hire_recommendation": "建议培养",
}


def generate_report(interview_data: dict[str, Any]) -> dict[str, Any]:
    """生成完整面试报告。

    interview_data 建议包含：
    {candidate, job, answers: [{round_no, category, question, answer_text, score, feedback}], total_score}
    返回：candidate/job/total_score/level/dimension_scores/radar_scores/answer_count/
          answers/overall_comment/strengths/weaknesses/suggestions/hire_recommendation/generated_at
    """
    answers = interview_data.get("answers", [])
    agg = scoring.aggregate(answers)

    # 组装供 LLM 的数据摘要
    transcript = "\n".join(
        f"【{a.get('category', '')}】{a.get('question', '')}\n答：{a.get('answer_text', '')}\n"
        f"得分：{a.get('score', 0)}\n"
        for a in answers
    )
    context = (
        f"候选人：{interview_data.get('candidate', '')}\n"
        f"岗位：{interview_data.get('job', '')}\n"
        f"总分：{agg['total_score']}（{scoring.level_from_score(agg['total_score'])}级）\n"
        f"维度得分：{agg['dimension_scores']}\n"
        f"面试记录：\n{transcript[:6000]}"
    )

    try:
        ai_part = llm.chat_json(
            [
                {"role": "system", "content": _REPORT_SYSTEM},
                {"role": "user", "content": context},
            ],
            temperature=0.4,
        )
        if not isinstance(ai_part, dict):
            raise ValueError(f"LLM 返回非字典: {type(ai_part).__name__}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("报告 AI 部分降级: %s", exc)
        ai_part = _rule_report(agg)

    # 补齐 AI 字段缺失（LLM 可能只返回部分字段）
    ai_part = {**_AI_DEFAULTS, **{k: v for k, v in (ai_part or {}).items() if v is not None}}

    # 雷达图数据：补全 5 个标准维度，未考核维度记 0
    radar_scores: dict[str, float] = {dim: 0.0 for dim in scoring.CATEGORY_DIMENSION.values()}
    radar_scores.update(agg["dimension_scores"])

    return {
        "candidate": interview_data.get("candidate", ""),
        "job": interview_data.get("job", ""),
        "generated_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_score": agg["total_score"],
        "level": scoring.level_from_score(agg["total_score"]),
        "dimension_scores": agg["dimension_scores"],
        "radar_scores": radar_scores,
        "answer_count": agg["answer_count"],
        "answers": answers,
        **ai_part,
    }
