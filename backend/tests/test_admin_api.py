"""后台管理接口冒烟测试（成员B）。

用法：pytest backend/tests/ -v
"""
from __future__ import annotations

import io

from backend.app.services import resume_parser


def test_create_and_list_enterprise(client):
    resp = client.post("/api/admin/enterprises", json={"name": "测试企业", "industry": "软件"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["name"] == "测试企业"
    ent_id = body["data"]["id"]

    resp = client.get("/api/admin/enterprises", params={"keyword": "测试"})
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["id"] == ent_id


def test_enterprise_update_and_delete_guard(client):
    ent = client.post("/api/admin/enterprises", json={"name": "E公司"}).json()["data"]
    client.post("/api/admin/jobs", json={"enterprise_id": ent["id"], "title": "J岗位"})

    # 更新企业
    resp = client.put(f"/api/admin/enterprises/{ent['id']}", json={"industry": "AI"})
    assert resp.json()["data"]["industry"] == "AI"

    # 有岗位时不能删企业
    resp = client.delete(f"/api/admin/enterprises/{ent['id']}")
    assert resp.json()["code"] == 1001


def test_create_and_list_job(client):
    ent = client.post("/api/admin/enterprises", json={"name": "A公司"}).json()["data"]
    resp = client.post("/api/admin/jobs", json={"enterprise_id": ent["id"], "title": "后端开发"})
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["title"] == "后端开发"

    resp = client.get("/api/admin/jobs", params={"enterprise_id": ent["id"]})
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["enterprise_name"] == "A公司"


def test_create_job_rejects_missing_enterprise(client):
    resp = client.post("/api/admin/jobs", json={"enterprise_id": 9999, "title": "x"})
    body = resp.json()
    assert body["code"] == 1002


def test_interviewer_crud(client):
    resp = client.post("/api/admin/interviewers", json={"name": "王老师", "role": "teacher"})
    assert resp.json()["code"] == 0
    iid = resp.json()["data"]["id"]

    assert client.get("/api/admin/interviewers").json()["data"]["total"] == 1

    resp = client.put(f"/api/admin/interviewers/{iid}", json={"title": "教授"})
    assert resp.json()["data"]["title"] == "教授"

    assert client.delete(f"/api/admin/interviewers/{iid}").json()["code"] == 0
    assert client.get("/api/admin/interviewers").json()["data"]["total"] == 0


def test_question_crud(client):
    resp = client.post(
        "/api/admin/questions",
        json={"category": "technical", "question": "什么是REST", "difficulty": 3},
    )
    assert resp.json()["code"] == 0
    qid = resp.json()["data"]["id"]

    resp = client.get("/api/admin/questions", params={"category": "technical"})
    assert resp.json()["data"]["total"] == 1

    resp = client.put(f"/api/admin/questions/{qid}", json={"difficulty": 5})
    assert resp.json()["data"]["difficulty"] == 5

    assert client.delete(f"/api/admin/questions/{qid}").json()["code"] == 0
    assert client.get("/api/admin/questions").json()["data"]["total"] == 0


def test_resume_upload_and_candidate_flow(client, monkeypatch):
    def fake_parse_resume(text: str) -> dict:
        return {
            "name": "张三",
            "email": "zhang@test.com",
            "phone": "13800138000",
            "education": [],
            "projects": [],
            "skills": ["Python"],
            "summary": "测试",
            "rule_only": True,
        }

    monkeypatch.setattr(resume_parser, "parse_resume", fake_parse_resume)

    files = {"file": ("resume.txt", io.BytesIO("简历正文".encode("utf-8")), "text/plain")}
    resp = client.post("/api/candidate/resume", files=files, data={"name": "李四"})
    body = resp.json()
    assert body["code"] == 0
    cid = body["data"]["candidate_id"]
    assert cid > 0
    assert body["data"]["name"] == "李四"
    assert body["data"]["email"] == "zhang@test.com"
    assert body["data"]["phone"] == "13800138000"

    resp = client.get(f"/api/admin/candidates/{cid}")
    assert resp.json()["data"]["id"] == cid

    resp = client.put(f"/api/admin/candidates/{cid}", json={"status": "closed"})
    assert resp.json()["data"]["status"] == "closed"


def test_resume_upload_updates_existing_candidate(client, monkeypatch):
    def fake_parse_resume(text: str) -> dict:
        return {
            "name": "张三",
            "email": "zhang@test.com",
            "phone": "13800138000",
            "education": [],
            "projects": [],
            "skills": [],
            "summary": "",
            "rule_only": True,
        }

    monkeypatch.setattr(resume_parser, "parse_resume", fake_parse_resume)

    files = {"file": ("resume.txt", io.BytesIO(b"x"), "text/plain")}
    first = client.post("/api/candidate/resume", files=files, data={"email": "zhang@test.com"}).json()
    second = client.post("/api/candidate/resume", files=files, data={"name": "张三丰"}).json()
    assert second["data"]["candidate_id"] == first["data"]["candidate_id"]
    assert second["data"]["name"] == "张三丰"
