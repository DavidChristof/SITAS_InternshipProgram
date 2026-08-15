"""服务层全链路测试（成员A，阶段四·任务11/12）。

用 mock 的 LLM 验证各服务函数降级逻辑，并跑通
  parse_resume → build_job_profile → plan_interview → evaluate_answer → scoring.aggregate → generate_report
全链路在无 key（LLM 失败）时也不抛异常、返回结构符合接口契约（docs/计划与分工.md 5.2 节）。
"""
import pytest

from backend.app import rag
from backend.app.services import (
    interview_agent,
    job_profiler,
    report,
    resume_parser,
    scoring,
    sql_agent,
    voice,
)
from backend.app.utils import llm

RESUME_TEXT = """张三，计算机科学与技术本科。
电话 138-0000-0000，邮箱 zhangsan@example.com。
熟悉 Python、FastAPI、MySQL，5 年左右后端开发经验。
项目：校园图书管理系统，担任后端负责人，负责 REST API 与数据库设计，支撑 1000+ 用户。
实习：某科技公司后端开发实习生，参与订单模块接口开发。
"""

JOB = {
    "id": 1,
    "title": "Python 后端开发工程师",
    "description": "负责后端系统设计与开发，要求熟悉 Python、FastAPI、SQL。",
    "skills": "Python, FastAPI, MySQL",
}


@pytest.fixture(scope="module", autouse=True)
def _knowledge():
    """用真实 data/knowledge 构建索引，供证据链检索。"""
    rag.knowledge_base.build_index()


def _no_llm(monkeypatch):
    """模拟无 DEEPSEEK_API_KEY：所有 LLM 调用都抛错。"""

    def boom(*args, **kwargs):
        raise RuntimeError("mock: 未配置 API Key")

    monkeypatch.setattr(llm, "chat", boom)
    monkeypatch.setattr(llm, "chat_json", boom)


def _answers_from_rounds(rounds) -> list[dict]:
    answers = []
    for r in rounds:
        ev = interview_agent.evaluate_answer(
            question=r["question"],
            answer="我在项目中负责后端接口开发，用 FastAPI 实现 REST API，解决了接口性能瓶颈，并补充了量化结果。",
            category=r["category"],
            expected_points=r["expected_points"],
        )
        answers.append(
            {
                "round_no": r["round_no"],
                "category": r["category"],
                "question": r["question"],
                "answer_text": "我在项目中负责后端接口开发，用 FastAPI 实现 REST API，解决了接口性能瓶颈，并补充了量化结果。",
                "score": ev["score"],
                "feedback": ev["feedback"],
            }
        )
    return answers


class TestFullPipelineNoLLM:
    """任务11：无 key 时全链路不抛异常，报告结构完整。"""

    def test_pipeline_degrades_gracefully(self, monkeypatch):
        _no_llm(monkeypatch)

        resume = resume_parser.parse_resume(RESUME_TEXT)
        assert "name" in resume and "skills" in resume

        profile = job_profiler.build_job_profile(JOB)
        assert profile["title"] and profile["core_skills"]

        rounds = interview_agent.plan_interview(profile, resume)
        assert len(rounds) == 5
        for r in rounds:
            assert {"round_no", "category", "question", "expected_points", "evidence"} <= set(r)
            assert r["question"]

        answers = _answers_from_rounds(rounds)
        agg = scoring.aggregate(answers)
        assert "total_score" in agg and "dimension_scores" in agg

        rep = report.generate_report({"candidate": "张三", "job": profile["title"], "answers": answers})
        for key in [
            "total_score", "level", "dimension_scores", "radar_scores", "answer_count",
            "overall_comment", "strengths", "weaknesses", "suggestions", "hire_recommendation",
        ]:
            assert key in rep, f"报告缺少 {key}"
        assert rep["hire_recommendation"] in ("建议录用", "建议培养", "暂不匹配")
        assert len(rep["radar_scores"]) == 5  # 雷达图 5 个维度

    def test_generate_followup_degrades(self, monkeypatch):
        _no_llm(monkeypatch)
        ctx = [{"round_no": 1, "category": "project", "question": "介绍项目", "answer_text": "用了 FastAPI"}]
        result = interview_agent.generate_followup(ctx, {"title": "Python 后端"})
        assert {"question", "reason"} <= set(result)
        assert result["question"]

    def test_sql_agent_degrades(self, monkeypatch):
        _no_llm(monkeypatch)
        result = sql_agent.ask("各岗位平均分")
        assert {"question", "sql", "columns", "rows", "explanation"} <= set(result)
        # 降级到规则查询：sql 为内置规则（SELECT 开头）或明确说明
        assert result["sql"] == "" or result["sql"].upper().startswith("SELECT")

    def test_voice_degrades(self):
        # faster-whisper 未安装/模型不可用时返回空串，绝不抛异常
        assert voice.transcribe("不存在.wav") == ""


class TestFullPipelineWithLLM:
    """任务11：有 LLM（mock 成功）时全链路字段能正确串联。"""

    def test_pipeline_threads_llm_values(self, monkeypatch):
        monkeypatch.setattr(llm, "chat", lambda messages, **kw: "请谈谈你在 Python 后端方面的经验与项目实践。")
        monkeypatch.setattr(
            llm, "chat_json",
            lambda messages, **kw: {"score": 85, "feedback": "回答较好", "improvement": "可补充量化", "missing_points": ["量化"]},
        )

        resume = resume_parser.parse_resume(RESUME_TEXT)
        profile = job_profiler.build_job_profile(JOB)
        rounds = interview_agent.plan_interview(profile, resume)

        answers = _answers_from_rounds(rounds)
        rep = report.generate_report({"candidate": "张三", "job": profile["title"], "answers": answers})

        # 报告应透传评分与回答
        assert rep["answer_count"] == 5
        assert all(a["score"] == 85 for a in rep["answers"])
        assert rep["total_score"] == 85.0
        assert rep["level"] == "A"

    def test_llm_question_used_when_no_bank(self, monkeypatch):
        # 题库没有匹配题时（无证据可复用），出题走 LLM 文案
        monkeypatch.setattr(interview_agent, "_category_evidence", lambda cat, profile: [])
        monkeypatch.setattr(llm, "chat", lambda messages, **kw: "请谈谈你在 Python 后端方面的经验与项目实践。")
        monkeypatch.setattr(
            llm, "chat_json",
            lambda messages, **kw: {"score": 70, "feedback": "ok", "improvement": "x", "missing_points": []},
        )
        rounds = interview_agent.plan_interview(
            job_profiler.build_job_profile(JOB),
            resume_parser.parse_resume(RESUME_TEXT),
        )
        tech = next(r for r in rounds if r["category"] == "technical")
        assert "Python" in tech["question"] or "后端" in tech["question"]


class TestContract:
    """接口契约自测（docs/计划与分工.md 5.2 节）。"""

    def test_resume_parser_contract(self, monkeypatch):
        _no_llm(monkeypatch)
        data = resume_parser.parse_resume(RESUME_TEXT)
        for key in ["name", "education", "projects", "skills", "internships", "summary"]:
            assert key in data, f"简历画像缺少 {key}"

    def test_job_profile_contract(self, monkeypatch):
        _no_llm(monkeypatch)
        data = job_profiler.build_job_profile(JOB)
        for key in ["title", "core_skills", "capability_dimensions", "interview_focus", "suggested_rounds"]:
            assert key in data, f"岗位画像缺少 {key}"

    def test_evaluate_answer_contract(self, monkeypatch):
        _no_llm(monkeypatch)
        ev = interview_agent.evaluate_answer(question="q", answer="比较完整的回答内容用于评分路径测试。", category="technical")
        assert set(ev) >= {"score", "feedback", "improvement", "missing_points", "evidence"}
        assert 0 <= ev["score"] <= 100

    def test_scoring_contract(self):
        agg = scoring.aggregate([{"category": "technical", "score": 80}, {"category": "project", "score": 60}])
        assert set(agg) == {"total_score", "dimension_scores", "answer_count"}
        assert agg["answer_count"] == 2

    def test_report_contract(self, monkeypatch):
        _no_llm(monkeypatch)
        rep = report.generate_report({})
        assert "hire_recommendation" in rep and "radar_scores" in rep

    def test_sql_contract_requires_no_db(self, monkeypatch):
        # SQL Agent 失败也返回结构化错误，不抛给 API 层
        def boom(*args, **kwargs):
            raise RuntimeError("mock: 无 key")

        monkeypatch.setattr(llm, "chat", boom)
        result = sql_agent.ask("今天的天气")
        assert set(result) == {"question", "sql", "columns", "rows", "explanation"}

    def test_knowledge_base_search(self):
        docs = rag.knowledge_base.search("FastAPI 面试题", top_k=3)
        assert isinstance(docs, list)
        for d in docs:
            assert {"id", "title", "content", "source"} <= set(d)


class TestNoKeyNoThrow:
    """验收：无 DEEPSEEK_API_KEY 时所有服务函数仍返回合理结果。"""

    @pytest.mark.parametrize(
        "call",
        [
            lambda: resume_parser.parse_resume(""),
            lambda: job_profiler.build_job_profile({}),
            lambda: interview_agent.plan_interview({}, {}),
            lambda: interview_agent.generate_followup([], {}),
            lambda: interview_agent.evaluate_answer("q", ""),
            lambda: scoring.aggregate([]),
            lambda: report.generate_report({}),
            lambda: sql_agent.ask(""),
            lambda: voice.transcribe(""),
        ],
    )
    def test_service_never_throws(self, monkeypatch, call):
        _no_llm(monkeypatch)
        result = call()
        assert result is not None
