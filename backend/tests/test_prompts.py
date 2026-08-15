"""提示词模板与 interview_agent 字段对齐测试（成员A）。

用 mock 的 LLM 验证：
1. plan_interview 能生成 5 个环节的问题序列（结构符合契约）
2. evaluate_answer 对 5 种环节都不会因模板变量缺失抛 KeyError
3. 评分结构字段齐全、score 在 0-100 之间

真实效果需配置 DEEPSEEK_API_KEY 后人工验证（本测试不消耗 token）。
"""
import pytest

from backend.app.services import interview_agent
from backend.app.utils import llm

SAMPLE_JOB = {
    "title": "Python 后端开发工程师",
    "core_skills": ["Python", "FastAPI", "SQL"],
    "capability_dimensions": [{"name": "专业能力", "weight": 0.5, "description": "后端开发"}],
    "interview_focus": ["Python 基础", "数据库", "项目经验"],
    "suggested_rounds": ["self_intro", "project", "technical", "behavioral", "reverse"],
}

SAMPLE_RESUME = {
    "name": "张三",
    "summary": "计算机专业应届生，熟悉 Python 与 FastAPI，有校园项目经验",
    "skills": ["Python", "FastAPI"],
    "projects": [
        {
            "name": "校园图书管理系统",
            "role": "后端负责人",
            "tech_stack": ["Python", "FastAPI"],
            "description": "负责 REST API 与数据库设计，支撑 1000+ 用户",
        }
    ],
    "education": [],
    "internships": [],
}

_FAKE_JSON = {"score": 85, "feedback": "回答不错", "improvement": "补充量化结果", "missing_points": ["量化"]}


def _fake_llm(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda messages, **kw: "请简单介绍一下你在项目中的角色与贡献。")
    monkeypatch.setattr(llm, "chat_json", lambda messages, **kw: dict(_FAKE_JSON))


class TestPlanInterview:
    def test_generates_five_rounds(self, monkeypatch):
        _fake_llm(monkeypatch)
        rounds = interview_agent.plan_interview(SAMPLE_JOB, SAMPLE_RESUME)
        assert len(rounds) == 5
        for r in rounds:
            assert set(r) >= {"round_no", "category", "question", "expected_points", "evidence"}
            assert r["question"]
            assert r["round_no"] >= 1

    def test_self_intro_is_first(self, monkeypatch):
        _fake_llm(monkeypatch)
        rounds = interview_agent.plan_interview(SAMPLE_JOB, SAMPLE_RESUME)
        assert rounds[0]["category"] == "self_intro"

    def test_empty_resume_does_not_crash(self, monkeypatch):
        _fake_llm(monkeypatch)
        rounds = interview_agent.plan_interview(SAMPLE_JOB, {})
        assert len(rounds) == 5


class TestEvaluateAnswer:
    @pytest.mark.parametrize("cat", ["self_intro", "project", "technical", "behavioral", "reverse"])
    def test_no_keyerror_for_all_categories(self, monkeypatch, cat):
        """修复历史 bug：PROJECT_EVALUATE 曾引用缺失的 {project_brief} 导致全部走降级。"""
        _fake_llm(monkeypatch)
        result = interview_agent.evaluate_answer(
            question="请简述你在项目中的工作",
            answer="我负责后端的接口开发与数据库设计，用 FastAPI 实现……",
            category=cat,
            expected_points="贡献,难点,结果",
            job_title=SAMPLE_JOB["title"],
        )
        assert isinstance(result, dict)
        assert 0 <= result["score"] <= 100
        assert "feedback" in result and "improvement" in result
        assert "evidence" in result

    def test_empty_answer_returns_zero(self):
        result = interview_agent.evaluate_answer(question="q", answer="  ")
        assert result["score"] == 0

    def test_degrade_path_when_llm_fails(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        result = interview_agent.evaluate_answer(
            question="q", answer="这是一个足够长的回答，用来走降级分支的评分路径。", category="technical"
        )
        assert 0 <= result["score"] <= 100
        assert "降级" in result["feedback"]
