"""面试流程接口测试（成员B）：创建面试、历史、开始面试状态机。"""
from __future__ import annotations

from backend.app.services import interview_agent, job_profiler, resume_parser


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
    return cand["candidate_id"], job["id"]


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
    assert body["data"][0]["interview_id"] == iid
    assert body["data"][0]["job_title"] == "后端开发"
    assert body["data"][0]["status"] == "pending"


def test_create_interview_rejects_missing_candidate(client, monkeypatch):
    _, jid = _seed(client, monkeypatch)
    resp = client.post("/api/candidate/interview", json={"candidate_id": 9999, "job_id": jid})
    assert resp.json()["code"] == 1001


def test_start_interview(client, monkeypatch):
    cid, jid = _seed(client, monkeypatch)
    iid = client.post("/api/candidate/interview", json={"candidate_id": cid, "job_id": jid}).json()["data"]["interview_id"]

    def fake_build_job_profile(job) -> dict:
        return {"title": "后端", "core_skills": ["Python"], "interview_focus": [], "suggested_rounds": []}

    def fake_plan_interview(job_profile, resume_profile, categories=None) -> list[dict]:
        return [
            {"round_no": 1, "category": "self_intro", "question": "请自我介绍", "expected_points": "表达", "evidence": []},
            {"round_no": 2, "category": "technical", "question": "什么是REST", "expected_points": "概念", "evidence": []},
        ]

    monkeypatch.setattr(job_profiler, "build_job_profile", fake_build_job_profile)
    monkeypatch.setattr(interview_agent, "plan_interview", fake_plan_interview)

    resp = client.post(f"/api/interview/{iid}/start")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["question"] == "请自我介绍"
    assert body["data"]["total_rounds"] == 2

    # 状态应为 running，且后台可见
    resp = client.get("/api/admin/interviews", params={"status": "running"})
    assert resp.json()["data"]["total"] == 1

    # 详情里应有两道题
    resp = client.get(f"/api/admin/interviews/{iid}")
    detail = resp.json()["data"]
    assert detail["status"] == "running"
    assert len(detail["answers"]) == 2


def test_start_interview_twice_rejected(client, monkeypatch):
    cid, jid = _seed(client, monkeypatch)
    iid = client.post("/api/candidate/interview", json={"candidate_id": cid, "job_id": jid}).json()["data"]["interview_id"]

    monkeypatch.setattr(job_profiler, "build_job_profile", lambda job: {"title": "x", "core_skills": [], "interview_focus": [], "suggested_rounds": []})
    monkeypatch.setattr(interview_agent, "plan_interview", lambda a, b, categories=None: [
        {"round_no": 1, "category": "self_intro", "question": "q", "expected_points": "", "evidence": []}
    ])

    assert client.post(f"/api/interview/{iid}/start").json()["code"] == 0
    resp = client.post(f"/api/interview/{iid}/start")
    assert resp.json()["code"] == 1001
