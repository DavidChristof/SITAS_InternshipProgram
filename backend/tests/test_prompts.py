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


class TestEvidenceChain:
    """plan_interview 按环节检索知识库依据（evidence 链）。"""

    QUESTION_TECH = {
        "id": "questions/py_fastapi_flask",
        "title": "FastAPI 面试题",
        "content": "请简述 FastAPI 与 Flask 的区别。",
        "source": "面试题库",
        "meta": {"category": "technical", "expected_points": "异步,自动文档,类型校验"},
    }
    COMPANY_DOC = {
        "id": "companies/example",
        "title": "示例企业",
        "content": "公司是一家专注 AI 的科技公司，注重工程师文化、技术成长与团队协作。",
        "source": "企业资料",
        "meta": {},
    }
    GENERIC = {
        "id": "jobs/python",
        "title": "岗位JD",
        "content": "负责后端系统开发，有项目经验者优先。",
        "source": "岗位JD",
        "meta": {},
    }

    def _fake_search(self, query, top_k=3):
        if "企业资料" in query:
            return [self.COMPANY_DOC]
        if "面试题" in query:
            return [self.QUESTION_TECH]
        return [self.GENERIC]

    def test_every_round_has_trimmed_evidence(self, monkeypatch):
        _fake_llm(monkeypatch)
        monkeypatch.setattr(interview_agent.knowledge_base, "search", self._fake_search)
        rounds = interview_agent.plan_interview(SAMPLE_JOB, SAMPLE_RESUME)
        assert len(rounds) == 5
        for r in rounds:
            assert r["evidence"], f"{r['category']} 轮缺少证据"
            assert 0 < len(r["evidence"]) <= 3
            for e in r["evidence"]:
                assert len(e["content"]) <= 200

    def test_reverse_evidence_is_company(self, monkeypatch):
        _fake_llm(monkeypatch)
        monkeypatch.setattr(interview_agent.knowledge_base, "search", self._fake_search)
        rounds = interview_agent.plan_interview(SAMPLE_JOB, SAMPLE_RESUME)
        reverse = rounds[-1]
        assert reverse["category"] == "reverse"
        assert reverse["evidence"][0]["source"] == "企业资料"

    def test_technical_reuses_bank_question(self, monkeypatch):
        _fake_llm(monkeypatch)
        monkeypatch.setattr(interview_agent.knowledge_base, "search", self._fake_search)
        rounds = interview_agent.plan_interview(SAMPLE_JOB, SAMPLE_RESUME)
        tech = next(r for r in rounds if r["category"] == "technical")
        assert tech["question"] == "请简述 FastAPI 与 Flask 的区别。"

    def test_reuse_respects_category(self, monkeypatch):
        # 检索到的题是 behavioral，technical 环节不应复用，应走 LLM 生成
        behavioral_doc = {
            "id": "questions/behavioral",
            "title": "行为面试题",
            "content": "请分享一个你与团队产生分歧并解决的经历。",
            "source": "面试题库",
            "meta": {"category": "behavioral"},
        }

        def search_only_behavioral(query, top_k=3):
            return [behavioral_doc]

        _fake_llm(monkeypatch)
        monkeypatch.setattr(interview_agent.knowledge_base, "search", search_only_behavioral)
        rounds = interview_agent.plan_interview(SAMPLE_JOB, SAMPLE_RESUME)
        tech = next(r for r in rounds if r["category"] == "technical")
        assert tech["question"] == "请简单介绍一下你在项目中的角色与贡献。"

    def test_evidence_trimmed_when_long(self, monkeypatch):
        long_doc = dict(self.COMPANY_DOC, content="很长的内容" * 200)
        monkeypatch.setattr(
            interview_agent.knowledge_base, "search", lambda query, top_k=3: [long_doc]
        )
        _fake_llm(monkeypatch)
        rounds = interview_agent.plan_interview(SAMPLE_JOB, SAMPLE_RESUME)
        for r in rounds:
            for e in r["evidence"]:
                assert len(e["content"]) <= 200


class TestFollowup:
    """generate_followup 结构化追问 + 规则降级。"""

    CTX = [
        {
            "round_no": 1,
            "category": "technical",
            "question": "请简述 FastAPI 与 Flask 的区别",
            "answer_text": "FastAPI 是异步框架，有自动文档，性能更好。",
        }
    ]

    def test_returns_structured_followup(self, monkeypatch):
        def fake_chat_json(messages, **kw):
            return {"question": "具体性能提升了多少？", "reason": "回答提到性能更好但缺少量化"}

        monkeypatch.setattr(llm, "chat_json", fake_chat_json)
        result = interview_agent.generate_followup(self.CTX, SAMPLE_JOB)
        assert result == {"question": "具体性能提升了多少？", "reason": "回答提到性能更好但缺少量化"}

    def test_degrades_when_llm_garbage(self, monkeypatch):
        monkeypatch.setattr(llm, "chat_json", lambda messages, **kw: ["garbage"])
        result = interview_agent.generate_followup(self.CTX, SAMPLE_JOB)
        assert "question" in result and "reason" in result

    def test_degrades_on_empty_answer(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        ctx = [{"round_no": 1, "answer_text": "  "}]
        result = interview_agent.generate_followup(ctx, SAMPLE_JOB)
        assert "展开" in result["question"]
        assert "降级" in result["reason"]

    def test_degrades_on_short_answer(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        result = interview_agent.generate_followup([{"round_no": 1, "answer_text": "还行"}], SAMPLE_JOB)
        assert "展开" in result["question"]

    def test_degrades_on_missing_quantification(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        long_no_num = "在项目中我们遇到了接口响应变慢的问题，我负责用日志和监控定位瓶颈，并做了缓存与异步改造。"  # 无数字/量化词，且长度>30
        result = interview_agent.generate_followup([{"round_no": 1, "answer_text": long_no_num}], SAMPLE_JOB)
        assert "数据" in result["question"]

    def test_empty_context_no_crash(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        result = interview_agent.generate_followup([], SAMPLE_JOB)
        assert "question" in result

    def test_degrade_path_when_llm_fails(self, monkeypatch):
        def boom(messages, **kw):
            raise RuntimeError("mock 失败")

        monkeypatch.setattr(llm, "chat_json", boom)
        result = interview_agent.evaluate_answer(
            question="q", answer="这是一个足够长的回答，用来走降级分支的评分路径。", category="technical"
        )
        assert 0 <= result["score"] <= 100
        assert "降级" in result["feedback"]
