"""面试流程 API（成员B实现；AI 逻辑调用成员A的 services/interview_agent.py）。

面试状态机（成员B落地）：pending → running → finished
    POST /api/interview/{id}/start        开始面试 → 返回第一题（调用 agent.plan_interview）
    POST /api/interview/{id}/answer       提交一题回答 body:{round_no, answer_text, audio_url}
                                         → 返回 {score, feedback, next_question|END}
    GET  /api/interview/{id}/report       生成/获取面试报告（调用 services/report.py）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import fail, ok

router = APIRouter(prefix="/api/interview", tags=["面试流程"])


@router.get("/ping")
def ping():
    return ok({"pong": True})
