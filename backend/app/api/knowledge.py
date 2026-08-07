"""知识库检索 API（成员B实现，检索逻辑调用成员A的 rag/）。

接口契约：
    GET  /api/knowledge/search?q=关键词&top_k=5   全库检索，返回文档及命中依据
    POST /api/knowledge/build                    手动重建索引（管理员）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import fail, ok

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("/ping")
def ping():
    return ok({"pong": True})
