"""后台管理与候选人端接口冒烟测试（成员B）。

用法：pytest backend/tests/ -v
使用独立内存 SQLite，不污染 data/sitas.db 演示数据。
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import models  # noqa: F401  注册全部模型
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.services import resume_parser

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def client():
    """每个用例使用独立干净的内存数据库。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


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
    # 表单 name 优先于解析结果；email/phone 由解析结果兜底
    assert body["data"]["name"] == "李四"
    assert body["data"]["email"] == "zhang@test.com"
    assert body["data"]["phone"] == "13800138000"
    assert body["data"]["profile"]["skills"] == ["Python"]

    # 后台查看候选人详情
    resp = client.get(f"/api/admin/candidates/{cid}")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == cid
    assert body["data"]["profile"]["name"] == "张三"

    # 后台更新候选人状态
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
    # 同邮箱 → 复用同一候选人，而非新建
    assert second["data"]["candidate_id"] == first["data"]["candidate_id"]
    assert second["data"]["name"] == "张三丰"
