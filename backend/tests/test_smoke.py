"""冒烟测试：验证服务能启动、健康检查与前端入口正常。

用法（项目根目录执行）：
    pytest backend/tests/ -v
"""
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_index_page():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "SITAS" in resp.text


def test_candidate_jobs_api():
    resp = client.get("/api/candidate/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert isinstance(body["data"], list)
