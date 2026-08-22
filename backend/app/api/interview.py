"""面试流程 API（成员B实现；AI 逻辑调用成员A的 services/）。

面试状态机（成员B落地）：pending → running → finished
    POST /api/interview/{id}/start        开始面试 → 返回第一题（调用 agent.plan_interview）
    POST /api/interview/{id}/answer       提交一题回答 body:{round_no, answer_text, audio_url}
                                         → 返回 {score, feedback, finished, next_round/next_category/next_question}
    GET  /api/interview/{id}/report       生成/获取面试报告（调用 services/report.py，适配前端契约）
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Candidate, Interview, InterviewAnswer, Interviewer, Job
from ..schemas import AnswerCreate, fail, ok
from ..services import interview_agent, job_profiler, report as report_service

router = APIRouter(prefix="/api/interview", tags=["面试流程"])

# 服务层等级 S/A/B/C → 前端中文等级
_LEVEL_CN = {"S": "优秀", "A": "优秀", "B": "良好", "C": "待提升"}


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
    # 本次面试归属的面试官（若有），供前端对话页展示"AI 面试官：张老师"
    interviewer = None
    if iv.interviewer_id:
        intr = db.get(Interviewer, iv.interviewer_id)
        if intr:
            interviewer = {"name": intr.name, "title": intr.title}
    return ok(
        {
            "interview_id": iv.id,
            "round_no": first["round_no"],
            "category": first["category"],
            "question": first["question"],
            "total_rounds": len(plan),
            "interviewer": interviewer,
        }
    )


@router.post("/{interview_id}/answer")
def submit_answer(interview_id: int, body: AnswerCreate, db: Session = Depends(get_db)):
    """提交一题回答：存答案 → 评分 → 返回下一题（或标记结束）。"""
    iv = db.get(Interview, interview_id)
    if iv is None:
        return fail(1002, "面试不存在")
    if iv.status != "running":
        return fail(1001, "面试未开始或已结束")

    # round_no 递增校验
    if body.round_no != iv.current_round:
        return fail(1001, f"当前应回答第 {iv.current_round} 题")

    ans = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.interview_id == iv.id,
            InterviewAnswer.round_no == body.round_no,
        )
        .first()
    )
    if ans is None:
        return fail(1002, "该轮题目不存在")

    # 解析 RAG 依据
    evidence: list = []
    if ans.evidence:
        try:
            evidence = json.loads(ans.evidence)
        except json.JSONDecodeError:
            evidence = []

    # 存答案 + 评分（成员A 函数永不抛异常）
    ans.answer_text = body.answer_text
    ans.audio_url = body.audio_url or ""
    result = interview_agent.evaluate_answer(
        question=ans.question,
        answer=body.answer_text,
        category=ans.category,
        expected_points=ans.expected_points,
        evidence=evidence,
    )
    ans.score = result.get("score", 0)
    ans.feedback = result.get("feedback", "")

    total_rounds = (
        db.query(InterviewAnswer).filter(InterviewAnswer.interview_id == iv.id).count()
    )
    finished = body.round_no >= total_rounds

    if finished:
        iv.status = "finished"
        resp = {
            "score": ans.score,
            "feedback": ans.feedback,
            "improvement": result.get("improvement", ""),
            "finished": True,
            "total_rounds": total_rounds,
        }
    else:
        iv.current_round = body.round_no + 1
        next_ans = (
            db.query(InterviewAnswer)
            .filter(
                InterviewAnswer.interview_id == iv.id,
                InterviewAnswer.round_no == iv.current_round,
            )
            .first()
        )
        resp = {
            "score": ans.score,
            "feedback": ans.feedback,
            "improvement": result.get("improvement", ""),
            "finished": False,
            "next_round": next_ans.round_no if next_ans else body.round_no + 1,
            "next_category": next_ans.category if next_ans else "",
            "next_question": next_ans.question if next_ans else "",
            "total_rounds": total_rounds,
        }

    db.commit()
    return ok(resp)


@router.get("/{interview_id}/report")
def get_report(interview_id: int, db: Session = Depends(get_db)):
    """生成/获取面试报告（调用成员A 的 report.generate_report，适配前端契约）。"""
    iv = db.get(Interview, interview_id)
    if iv is None:
        return fail(1002, "面试不存在")
    if iv.status != "finished":
        return fail(1001, "面试尚未结束，无法生成报告")

    # 本次面试归属的面试官（若有）
    interviewer_name = ""
    if iv.interviewer_id:
        intr = db.get(Interviewer, iv.interviewer_id)
        if intr:
            interviewer_name = f"{intr.name}（{intr.title}）" if intr.title else intr.name

    # 缓存命中：直接返回已生成的报告
    if iv.report_json:
        try:
            return ok(_adapt_report(json.loads(iv.report_json), iv.id, iv.status, interviewer_name))
        except json.JSONDecodeError:
            pass  # 缓存损坏则重新生成

    job = db.get(Job, iv.job_id)
    candidate = db.get(Candidate, iv.candidate_id)
    answers = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.interview_id == iv.id)
        .order_by(InterviewAnswer.round_no)
        .all()
    )
    interview_data = {
        "candidate": candidate.name if candidate else "",
        "job": job.title if job else "",
        "answers": [
            {
                "round_no": a.round_no,
                "category": a.category,
                "question": a.question,
                "answer_text": a.answer_text,
                "score": a.score,
                "feedback": a.feedback,
            }
            for a in answers
        ],
    }

    raw = report_service.generate_report(interview_data)
    iv.report_json = json.dumps(raw, ensure_ascii=False)
    db.commit()
    return ok(_adapt_report(raw, iv.id, iv.status, interviewer_name))


def _adapt_report(raw: dict, interview_id: int, status: str, interviewer_name: str = "") -> dict:
    """把成员A 的报告输出适配成成员C 前端契约的字段。"""
    radar = raw.get("radar_scores") or {}
    return {
        "id": interview_id,
        "job_title": raw.get("job", ""),
        "candidate_name": raw.get("candidate", ""),
        "interviewer": interviewer_name,  # 本次面试官（张老师（副教授）），空串表示未指定
        "status": status,
        "total_score": raw.get("total_score"),
        "level": _LEVEL_CN.get(raw.get("level", ""), raw.get("level", "")),
        "dimension_scores": [{"name": k, "score": v} for k, v in radar.items()],
        "strengths": raw.get("strengths", []),
        "weaknesses": raw.get("weaknesses", []),
        "suggestions": raw.get("suggestions", []),
        "hire_recommendation": raw.get("hire_recommendation", ""),
        "answers": raw.get("answers", []),
        "created_at": raw.get("generated_at", ""),
    }
