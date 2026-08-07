"""面试报告生成模块（成员A）。

职责：聚合候选人信息、逐题问答、维度得分，用 LLM 生成总体评价与改进建议，输出结构化报告。
"""
from __future__ import annotations

import logging
from typing import Any

from . import scoring
from ..utils import llm

_REPORT_SYSTEM = """你是资深 HR 专家。请基于以下面试数据撰写一份结构化人才评估报告（JSON）：
{
  "overall_comment": "总体评价（3-5句）",
  "strengths": ["优势数组"],
  "weaknesses": ["不足数组"],
  "suggestions": ["针对性改进建议数组"],
  "hire_recommendation": "建议录用 / 建议培养 / 暂不匹配"
}
"""


def generate_report(interview_data: dict[str, Any]) -> dict[str, Any]:
    """生成完整面试报告。

    interview_data 建议包含：
    {candidate, job, answers: [{round_no, category, question, answer_text, score, feedback}], total_score}
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
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("报告 AI 部分降级: %s", exc)
        ai_part = {"overall_comment": "（LLM 暂不可用，已生成基础报告）", "strengths": [], "weaknesses": [], "suggestions": [], "hire_recommendation": "建议培养"}

    return {
        "candidate": interview_data.get("candidate", ""),
        "job": interview_data.get("job", ""),
        "total_score": agg["total_score"],
        "level": scoring.level_from_score(agg["total_score"]),
        "dimension_scores": agg["dimension_scores"],
        "answer_count": agg["answer_count"],
        "answers": answers,
        **ai_part,
    }
