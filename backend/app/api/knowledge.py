"""知识库检索 API（成员B实现，检索逻辑调用成员A的 rag/）。

接口契约：
    GET  /api/knowledge/search?q=关键词&top_k=5   全库检索，返回文档及命中依据
    POST /api/knowledge/build                    手动重建索引（管理员）
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..rag import knowledge_base
from ..schemas import fail, ok

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("/search")
def search_knowledge(
    q: str = Query("", description="检索关键词"),
    top_k: int = Query(5, ge=1, le=20),
):
    """全库检索：返回命中文档（id/title/content/source/score/meta）及检索依据。"""
    keyword = q.strip()
    if not keyword:
        return fail(1001, "请输入检索关键词")
    hits = knowledge_base.search(keyword, top_k=top_k)
    return ok(hits)


@router.post("/build")
def rebuild_index():
    """手动重建知识库索引（管理员）。

    注意：当前成员A 的 retriever 为累积式（见 docs/联调问题记录.md #3），重复调用会累积文档。
    """
    count = knowledge_base.build_index()
    return ok({"indexed": count})
