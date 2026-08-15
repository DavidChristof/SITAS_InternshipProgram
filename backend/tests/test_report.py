"""报告生成测试（成员A，阶段三·任务8）。

覆盖：
1. LLM 成功时：返回字段齐全、radar_scores 补全 5 维度
2. LLM 返回部分字段时：缺省字段兜底
3. LLM 失败/脏数据时：按维度得分生成规则版优缺点与录用建议
4. 空答案不崩溃
"""
import pytest

from backend.app.services import report, scoring
from backend.app.utils import llm

SAMPLE_DATA = {
    "candidate": "张三",
    "job": "Python 后端开发工程师",
    "answers": [
        {
            "round_no": 1,
            "category": "technical",
            "question": "简述 FastAPI 与 Flask 的区别",
            "answer_text": "FastAPI 支持异步与自动文档，类型校验完善。",
            "score": 90,
            "feedback": "回答准确",
        },
        {
            "round_no": 2,
            "category": "project",
            "question": "介绍一个最有挑战的项目",
            "answer_text": "做了图书管理系统。",
            "score": 50,
            "feedback": "不够详细",
        },
    ],
}

_AI_OK = {
    "overall_comment": "候选人技术基础扎实，项目陈述略显单薄。",
    "strengths": ["技术基础扎实", "沟通清晰"],
    "weaknesses": ["项目描述缺少细节", "缺少量化结果"],
    "suggestions": ["补充项目数据", "多练习结构化表达"],
    "hire_recommendation": "建议培养",
}


def _answers_for(cat_scores: list[tuple[str, int]]) -> list[dict]:
    return [
        {"round_no": i + 1, "category": cat, "question": f"q{i}", "answer_text": "答案", "score": s}
        for i, (cat, s) in enumerate(cat_scores)
    ]


class TestReportLLM:
    def test_full_report_keys_and_radar(self, monkeypatch):
        monkeypatch.setattr(llm, "chat_json", lambda messages, **kw: dict(_AI_OK))
        result = report.generate_report(SAMPLE_DATA)

        # 必含字段
        for key in [
            "candidate", "job", "generated_at", "total_score", "level",
            "dimension_scores", "radar_scores", "answer_count", "answers",
            "overall_comment", "strengths", "weaknesses", "suggestions", "hire_recommendation",
        ]:
            assert key in result, f"缺少字段 {key}"

        # 雷达图：补全 5 个标准维度
        assert set(result["radar_scores"]) == set(scoring.CATEGORY_DIMENSION.values())
        assert result["radar_scores"]["专业能力"] == 90.0
        assert result["radar_scores"]["项目实践"] == 50.0
        assert result["radar_scores"]["表达能力"] == 0.0  # 未考维度记 0

        # 聚合结果与答案透传
        assert result["total_score"] == 70.0
        assert result["level"] == "B"
        assert result["answer_count"] == 2
        assert len(result["answers"]) == 2

    def test_partial_llm_fields_coerced(self, monkeypatch):
        # LLM 只返回部分字段，缺省字段应兜底
        monkeypatch.setattr(llm, "chat_json", lambda messages, **kw: {"overall_comment": "只有评语"})
        result = report.generate_report(SAMPLE_DATA)
        assert result["overall_comment"] == "只有评语"
        assert result["strengths"] == []
        assert result["weaknesses"] == []
        assert result["suggestions"] == []
        assert result["hire_recommendation"] == "建议培养"

    def test_llm_non_dict_degrades(self, monkeypatch):
        monkeypatch.setattr(llm, "chat_json", lambda messages, **kw: ["garbage"])
        result = report.generate_report(SAMPLE_DATA)
        # 降级路径：按维度分生成优缺点
        assert "专业能力 表现较好（90.0 分）" in result["strengths"]
        assert "项目实践 有待加强（50.0 分）" in result["weaknesses"]
        assert result["hire_recommendation"] == "建议培养"  # total 70 < 80


class TestReportDegrade:
    def test_degrade_derives_strengths_weaknesses(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        result = report.generate_report(SAMPLE_DATA)

        assert "专业能力 表现较好（90.0 分）" in result["strengths"]
        assert "项目实践 有待加强（50.0 分）" in result["weaknesses"]
        assert result["hire_recommendation"] == "建议培养"
        assert result["level"] == "B"

    def test_degrade_high_total_recommends_hire(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        high = _answers_for([("technical", 95), ("project", 85)])
        result = report.generate_report({"answers": high})
        assert result["total_score"] == 90.0
        assert result["level"] == "S"
        assert result["hire_recommendation"] == "建议录用"

    def test_degrade_low_total_recommends_no_match(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        low = _answers_for([("technical", 40), ("project", 30)])
        result = report.generate_report({"answers": low})
        assert result["total_score"] == 35.0
        assert result["hire_recommendation"] == "暂不匹配"

    def test_no_dimension_scores_gets_fallback_text(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        # 无答案：没有维度分，应输出兜底文案而非崩溃
        result = report.generate_report({"candidate": "李四", "answers": []})
        assert result["strengths"] == ["暂无显著优势维度"]
        assert result["weaknesses"] == ["暂无明显短板，需结合具体答题深入评估"]
        assert result["total_score"] == 0
        assert result["level"] == "C"


class TestReportEmpty:
    def test_empty_answers_no_crash(self):
        result = report.generate_report({})
        assert result["total_score"] == 0
        assert result["answer_count"] == 0
        assert set(result["radar_scores"]) == set(scoring.CATEGORY_DIMENSION.values())
        assert result["hire_recommendation"] in ("建议录用", "建议培养", "暂不匹配")

    def test_report_uses_aggregate_consistently(self):
        # 与 scoring.aggregate 结果保持一致
        agg = scoring.aggregate(SAMPLE_DATA["answers"])
        assert agg["total_score"] == 70.0
