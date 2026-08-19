"""知识库检索接口测试（成员B）。"""
from __future__ import annotations


def test_search_returns_hits(client):
    resp = client.get("/api/knowledge/search", params={"q": "Python"})
    body = resp.json()
    assert body["code"] == 0
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    # 每篇文档应含检索依据关键字段
    assert "title" in body["data"][0]
    assert "source" in body["data"][0]


def test_search_empty_query_rejected(client):
    resp = client.get("/api/knowledge/search", params={"q": "   "})
    assert resp.json()["code"] == 1001


def test_build_index(client):
    resp = client.post("/api/knowledge/build")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["indexed"] > 0
