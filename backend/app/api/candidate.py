"""候选人端 API（成员B实现，成员C前端调用）。

接口契约（成员C依赖，请保持路径/参数不变，改动需通知C）：
    POST /api/candidate/resume             上传简历（multipart，字段 file）→ 解析并返回候选人档案
    GET  /api/candidate/jobs               可投递岗位列表（含企业名）
    POST /api/candidate/interview          创建一场面试（body: {candidate_id, job_id}）→ 返回 interview_id
    GET  /api/candidate/interviews         我的面试历史（含状态、总分）
    GET  /api/candidate/interview/{id}     面试详情（逐题问答+评分+报告）（第三阶段）
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Candidate, Enterprise, Interview, Job
from ..schemas import InterviewCreate, fail, ok
from ..services import resume_parser

router = APIRouter(prefix="/api/candidate", tags=["候选人端"])


@router.get("/jobs")
def list_jobs(keyword: str = "", db: Session = Depends(get_db)):
    """可投递岗位列表（含企业名，可按岗位名搜索）。"""
    q = db.query(Job, Enterprise.name).join(Enterprise, Job.enterprise_id == Enterprise.id)
    if keyword:
        q = q.filter(Job.title.contains(keyword))
    rows = q.order_by(Job.id).limit(100).all()
    data = [
        {
            "id": j.id,
            "enterprise_id": j.enterprise_id,
            "enterprise_name": ename,
            "title": j.title,
            "skills": j.skills,
            "description": j.description,
        }
        for j, ename in rows
    ]
    return ok(data)


@router.post("/resume")
def upload_resume(
    file: UploadFile = File(...),
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    db: Session = Depends(get_db),
):
    """上传简历：保存文件 → 调成员A 解析 → 创建/更新候选人 → 返回档案。

    字段：file 必填；name/email/phone 可选（缺省时用解析结果兜底）。
    """
    # 1. 保存原始文件到 upload_dir（uuid 命名避免冲突，存相对路径）
    content = file.file.read()
    suffix = Path(file.filename or "resume.txt").suffix or ".txt"
    dest_name = f"{uuid.uuid4().hex}{suffix}"
    dest = Path(settings.upload_dir) / dest_name
    dest.write_bytes(content)

    # 2. 提取文本（utf-8，失败回退 gbk）
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="ignore")

    # 3. 调成员A 解析（永不抛异常；无 key 时降级为规则结果）
    profile = resume_parser.parse_resume(text)

    # 4. 字段兜底：表单值优先，缺省用解析结果
    final_name = name or profile.get("name") or ""
    final_email = email or profile.get("email") or ""
    final_phone = phone or profile.get("phone") or ""

    # 5. 创建/更新候选人（按邮箱匹配）
    cand = None
    if final_email:
        cand = db.query(Candidate).filter(Candidate.email == final_email).first()
    if cand is None:
        cand = Candidate(name=final_name, email=final_email, phone=final_phone)
        db.add(cand)
    else:
        cand.name = final_name or cand.name
        cand.phone = final_phone or cand.phone
    cand.resume_text = text
    cand.resume_file = dest_name
    cand.profile_json = json.dumps(profile, ensure_ascii=False)
    db.commit()
    db.refresh(cand)

    return ok(
        {
            "candidate_id": cand.id,
            "name": cand.name,
            "email": cand.email,
            "phone": cand.phone,
            "profile": profile,
        }
    )


@router.post("/interview")
def create_interview(body: InterviewCreate, db: Session = Depends(get_db)):
    """创建一场面试（pending 状态），返回 interview_id。"""
    if db.get(Candidate, body.candidate_id) is None:
        return fail(1001, "候选人不存在")
    if db.get(Job, body.job_id) is None:
        return fail(1001, "岗位不存在")
    iv = Interview(candidate_id=body.candidate_id, job_id=body.job_id, status="pending", current_round=0)
    db.add(iv)
    db.commit()
    db.refresh(iv)
    return ok({"interview_id": iv.id, "status": iv.status})


@router.get("/interviews")
def list_interviews(candidate_id: int = Query(...), db: Session = Depends(get_db)):
    """我的面试历史（含岗位名、状态、总分），按创建时间倒序。"""
    q = (
        db.query(Interview, Job.title)
        .join(Job, Interview.job_id == Job.id)
        .filter(Interview.candidate_id == candidate_id)
    )
    rows = q.order_by(Interview.id.desc()).all()
    items = []
    for iv, job_title in rows:
        report: dict = {}
        if iv.report_json:
            try:
                report = json.loads(iv.report_json)
            except json.JSONDecodeError:
                report = {}
        items.append(
            {
                "interview_id": iv.id,
                "job_id": iv.job_id,
                "job_title": job_title,
                "status": iv.status,
                "current_round": iv.current_round,
                "total_score": report.get("total_score"),
                "created_at": iv.created_at.isoformat() if iv.created_at else None,
            }
        )
    return ok(items)
