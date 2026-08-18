"""面试流程 API（成员B实现；AI 逻辑调用成员A的 services/interview_agent.py）。

面试状态机（成员B落地）：pending → running → finished
    POST /api/interview/{id}/start        开始面试 → 返回第一题（调用 agent.plan_interview）
    POST /api/interview/{id}/answer       提交一题回答 body:{round_no, answer_text, audio_url}
                                         → 返回 {score, feedback, next_question|END}（第三阶段）
    GET  /api/interview/{id}/report       生成/获取面试报告（第三阶段）
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Candidate, Interview, InterviewAnswer, Job
from ..schemas import fail, ok
from ..services import interview_agent, job_profiler

router = APIRouter(prefix="/api/interview", tags=["面试流程"])


@router.post("/{interview_id}/start")
def start_interview(interview_id: int, db: Session = Depends(get_db)):
    """开始面试：pending→running，生成题目序列并落库，返回第一题。"""
    iv = db.get(Interview, interview_id)
    if iv is None:
        return fail(1002, "面试不存在")
    if iv.status != "pending":
        return fail(1001, "面试已开始或已结束，无法重复开始")

    job = db.get(Job, iv.job_id)
    candidate = db.get(Candidate, iv.candidate_id)
    if job is None or candidate is None:
        return fail(1002, "岗位或候选人不存在")

    # 简历画像（解析失败按空画像处理）
    resume_profile: dict = {}
    if candidate.profile_json:
        try:
            resume_profile = json.loads(candidate.profile_json)
        except json.JSONDecodeError:
            resume_profile = {}

    # 岗位画像 + 出题（成员A 函数永不抛异常，无 key 时降级）
    job_profile = job_profiler.build_job_profile(job)
    plan = interview_agent.plan_interview(job_profile, resume_profile)

    if not plan:
        return fail(1003, "出题失败，请稍后重试")

    # 为每轮创建答题记录（先存题，答案在 answer 阶段回填）
    for r in plan:
        db.add(
            InterviewAnswer(
                interview_id=iv.id,
                round_no=r["round_no"],
                category=r["category"],
                question=r["question"],
                expected_points=r.get("expected_points", ""),
                evidence=json.dumps(r.get("evidence", []), ensure_ascii=False),
            )
        )

    iv.status = "running"
    iv.current_round = 1
    iv.started_at = datetime.now()
    db.commit()

    first = plan[0]
    return ok(
        {
            "interview_id": iv.id,
            "round_no": first["round_no"],
            "category": first["category"],
            "question": first["question"],
            "total_rounds": len(plan),
        }
    )
