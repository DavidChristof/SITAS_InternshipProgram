"""面试流程接口测试（成员B）：创建面试、历史、开始/作答/报告。"""
from __future__ import annotations

from backend.app.services import interview_agent, job_profiler, report as report_service
from backend.app.services import resume_parser


def _fake_parse_resume(text: str) -> dict:
    return {
        "name": "张三",
        "email": "zhang@test.com",
        "phone": "13800138000",
        "education": [],
        "projects": [],
        "skills": ["Python"],
        "summary": "后端候选人",
        "rule_only": True,
    }


def _fake_evaluate_answer(question, answer, category="technical", expected_points="", evidence=None) -> dict:
    return {
        "score": 85,
        "feedback": "回答不错",
        "improvement": "可以更好",
        "missing_points": [],
        "evidence": evidence or [],
    }


def _fake_generate_report(interview_data: dict) -> dict:
    return {
        "candidate": "张三",
        "job": "后端开发",
        "generated_at": "2026-08-19 10:00",
        "total_score": 85.0,
        "level": "A",
        "dimension_scores": {"专业能力": 85.0},
        "radar_scores": {"表达能力": 80, "项目实践": 85, "专业能力": 90, "综合素质": 85, "求职动机": 85},
        "answer_count": 2,
        "answers": interview_data["answers"],
        "overall_comment": "不错",
        "strengths": ["强"],
        "weaknesses": ["弱"],
        "suggestions": ["建议"],
        "hire_recommendation": "建议录用",
    }


def _seed(client, monkeypatch) -> tuple[int, int]:
    """准备演示数据：企业 + 岗位 + 候选人，返回 (candidate_id, job_id)。"""
    monkeypatch.setattr(resume_parser, "parse_resume", _fake_parse_resume)
    ent = client.post("/api/admin/enterprises", json={"name": "测试企业"}).json()["data"]
    job = client.post(
        "/api/admin/jobs", json={"enterprise_id": ent["id"], "title": "后端开发", "skills": "Python"}
    ).json()["data"]
    cand = client.post(
        "/api/candidate/resume", files={"file": ("r.txt", b"x", "text/plain")}
    ).json()["data"]
    return cand["id"], job["id"]


def _start_plan(monkeypatch, rounds: list[dict]) -> None:
    """打桩岗位画像与出题，返回固定题目序列。"""
    monkeypatch.setattr(
        job_profiler,
        "build_job_profile",
        lambda job: {"title": "后端", "core_skills": [], "interview_focus": [], "suggested_rounds": []},
    )
    monkeypatch.setattr(interview_agent, "plan_interview", lambda a, b, categories=None: rounds)


def test_create_interview_and_history(client, monkeypatch):
    cid, jid = _seed(client, monkeypatch)
    resp = client.post("/api/candidate/interview", json={"candidate_id": cid, "job_id": jid})
    body = resp.json()
    assert body["code"] == 0
    iid = body["data"]["interview_id"]
    assert iid > 0

    resp = client.get("/api/candidate/interviews", params={"candidate_id": cid})
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == iid
    assert body["data"][0]["job_title"] == "后端开发"
    assert body["data"][0]["status"] == "pending"


def test_create_interview_rejects_missing_candidate(client, monkeypatch):
    _, jid = _seed(client, monkeypatch)
    resp = client.post("/api/candidate/interview", json={"candidate_id": 9999, "job_id": jid})
    assert resp.json()["code"] == 1001


def test_start_interview(client, monkeypatch):
    cid, jid = _seed(client, monkeypatch)
    iid = client.post("/api/candidate/interview", json={"candidate_id": cid, "job_id": jid}).json()["data"]["interview_id"]

    _start_plan(
        monkeypatch,
        [
            {"round_no": 1, "category": "self_intro", "question": "请自我介绍", "expected_points": "表达", "evidence": []},
            {"round_no": 2, "category": "technical", "question": "什么是REST", "expected_points": "概念", "evidence": []},
        ],
    )

    resp = client.post(f"/api/interview/{iid}/start")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["question"] == "请自我介绍"
    assert body["data"]["total_rounds"] == 2

    resp = client.get("/api/admin/interviews", params={"status": "running"})
    assert resp.json()["data"]["total"] == 1

    detail = client.get(f"/api/admin/interviews/{iid}").json()["data"]
    assert detail["status"] == "running"
    assert len(detail["answers"]) == 2


def test_start_interview_twice_rejected(client, monkeypatch):
    cid, jid = _seed(client, monkeypatch)
    iid = client.post("/api/candidate/interview", json={"candidate_id": cid, "job_id": jid}).json()["data"]["interview_id"]

    _start_plan(
        monkeypatch,
        [{"round_no": 1, "category": "self_intro", "question": "q", "expected_points": "", "evidence": []}],
    )

    assert client.post(f"/api/interview/{iid}/start").json()["code"] == 0
    resp = client.post(f"/api/interview/{iid}/start")
    assert resp.json()["code"] == 1001


def test_answer_flow(client, monkeypatch):
    cid, jid = _seed(client, monkeypatch)
    iid = client.post("/api/candidate/interview", json={"candidate_id": cid, "job_id": jid}).json()["data"]["interview_id"]

    _start_plan(
        monkeypatch,
        [
            {"round_no": 1, "category": "self_intro", "question": "自我介绍", "expected_points": "表达", "evidence": []},
            {"round_no": 2, "category": "technical", "question": "什么是REST", "expected_points": "概念", "evidence": []},
        ],
    )
    monkeypatch.setattr(interview_agent, "evaluate_answer", _fake_evaluate_answer)

    assert client.post(f"/api/interview/{iid}/start").json()["code"] == 0

    # 第 1 题
    r1 = client.post(f"/api/interview/{iid}/answer", json={"round_no": 1, "answer_text": "我叫张三"}).json()["data"]
    assert r1["finished"] is False
    assert r1["score"] == 85
    assert r1["next_round"] == 2
    assert r1["next_category"] == "technical"
    assert r1["next_question"] == "什么是REST"

    # 第 2 题（最后一题）
    r2 = client.post(f"/api/interview/{iid}/answer", json={"round_no": 2, "answer_text": "REST是..."}).json()["data"]
    assert r2["finished"] is True
    assert r2["score"] == 85

    # 状态应 finished，且答案已入库
    detail = client.get(f"/api/admin/interviews/{iid}").json()["data"]
    assert detail["status"] == "finished"
    assert len(detail["answers"]) == 2
    assert detail["answers"][0]["score"] == 85
    assert detail["answers"][0]["answer_text"] == "我叫张三"


def test_answer_round_validation(client, monkeypatch):
    cid, jid = _seed(client, monkeypatch)
    iid = client.post("/api/candidate/interview", json={"candidate_id": cid, "job_id": jid}).json()["data"]["interview_id"]

    _start_plan(
        monkeypatch,
        [{"round_no": 1, "category": "self_intro", "question": "q", "expected_points": "", "evidence": []}],
    )
    client.post(f"/api/interview/{iid}/start")

    # 当前应回答第 1 题，提交 round_no=2 应被拒绝
    resp = client.post(f"/api/interview/{iid}/answer", json={"round_no": 2, "answer_text": "x"})
    assert resp.json()["code"] == 1001


def test_report(client, monkeypatch):
    cid, jid = _seed(client, monkeypatch)
    iid = client.post("/api/candidate/interview", json={"candidate_id": cid, "job_id": jid}).json()["data"]["interview_id"]

    _start_plan(
        monkeypatch,
        [{"round_no": 1, "category": "self_intro", "question": "q1", "expected_points": "", "evidence": []}],
    )
    monkeypatch.setattr(interview_agent, "evaluate_answer", _fake_evaluate_answer)
    monkeypatch.setattr(report_service, "generate_report", _fake_generate_report)

    # 未结束前生成报告应被拒绝
    client.post(f"/api/interview/{iid}/start")
    assert client.get(f"/api/interview/{iid}/report").json()["code"] == 1001

    # 作答结束
    client.post(f"/api/interview/{iid}/answer", json={"round_no": 1, "answer_text": "x"})

    resp = client.get(f"/api/interview/{iid}/report")
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["job_title"] == "后端开发"
    assert data["candidate_name"] == "张三"
    assert data["total_score"] == 85.0
    assert data["level"] == "优秀"  # level "A" -> 优秀
    assert isinstance(data["dimension_scores"], list)
    assert len(data["dimension_scores"]) == 5
    assert data["dimension_scores"][0]["name"] == "表达能力"
