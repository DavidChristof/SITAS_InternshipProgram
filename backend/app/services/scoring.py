"""评分汇总模块（成员A）。

职责：将各题评分聚合成总分、按维度统计，供报告生成与前端展示。
"""
from __future__ import annotations

from typing import Any

# 环节 -> 维度名（用于雷达图）
CATEGORY_DIMENSION: dict[str, str] = {
    "self_intro": "表达能力",
    "project": "项目实践",
    "technical": "专业能力",
    "behavioral": "综合素质",
    "reverse": "求职动机",
}


def aggregate(scores: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总各题评分。

    scores: [{category, score, feedback, ...}]
    返回 {total_score, dimension_scores: {维度: 平均分}, answer_count}
    """
    if not scores:
        return {"total_score": 0, "dimension_scores": {}, "answer_count": 0}

    dim_map: dict[str, list[float]] = {}
    for s in scores:
        cat = s.get("category", "technical")
        dim = CATEGORY_DIMENSION.get(cat, "专业能力")
        dim_map.setdefault(dim, []).append(float(s.get("score", 0)))

    dimension_scores = {d: round(sum(v) / len(v), 1) for d, v in dim_map.items()}
    total = sum(dimension_scores.values()) / len(dimension_scores) if dimension_scores else 0
    return {
        "total_score": round(total, 1),
        "dimension_scores": dimension_scores,
        "answer_count": len(scores),
    }


def level_from_score(total: float) -> str:
    """总分 -> 等级（S/A/B/C）。"""
    if total >= 90:
        return "S"
    if total >= 80:
        return "A"
    if total >= 70:
        return "B"
    return "C"
