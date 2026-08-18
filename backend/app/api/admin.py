"""HR/教师/管理员 后台管理 API（成员B实现，成员C前端调用）。

接口契约（成员C依赖）：
    企业：     GET/POST/PUT/DELETE /api/admin/enterprises[/{id}]
    岗位：     GET/POST/PUT/DELETE /api/admin/jobs[/{id}]
    候选人：   GET/PUT /api/admin/candidates[/{id}]
    面试官：   GET/POST/PUT/DELETE /api/admin/interviewers[/{id}]   （第二阶段）
    题库：     GET/POST/PUT/DELETE /api/admin/questions[/{id}]      （第二阶段）
    面试记录： GET /api/admin/interviews（可筛选 candidate_id/job_id/status）（第二阶段）

分页约定：GET 列表接口支持 ?page=1&size=10（page 从 1 起，size 默认 10、上限 100），
         返回 data = {"items": [...], "total": N, "page": 1, "size": 10}
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Candidate, Enterprise, Job
from ..schemas import CandidateUpdate, EnterpriseCreate, JobCreate, fail, ok

router = APIRouter(prefix="/api/admin", tags=["后台管理"])


def _iso(dt) -> str | None:
    """datetime → ISO 字符串（可空）。"""
    return dt.isoformat() if dt else None


# ============ 企业 ============


@router.get("/enterprises")
def list_enterprises(
    keyword: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """企业列表（分页 + 名称模糊搜索）。"""
    q = db.query(Enterprise)
    if keyword:
        q = q.filter(Enterprise.name.contains(keyword))
    total = q.count()
    rows = q.order_by(Enterprise.id).offset((page - 1) * size).limit(size).all()
    items = [
        {
            "id": e.id,
            "name": e.name,
            "industry": e.industry,
            "description": e.description,
            "created_at": _iso(e.created_at),
        }
        for e in rows
    ]
    return ok({"items": items, "total": total, "page": page, "size": size})


@router.post("/enterprises")
def create_enterprise(body: EnterpriseCreate, db: Session = Depends(get_db)):
    """新建企业，返回企业对象。"""
    ent = Enterprise(**body.model_dump())
    db.add(ent)
    db.commit()
    db.refresh(ent)
    return ok(
        {
            "id": ent.id,
            "name": ent.name,
            "industry": ent.industry,
            "description": ent.description,
            "created_at": _iso(ent.created_at),
        }
    )


# ============ 岗位 ============


@router.get("/jobs")
def list_jobs(
    keyword: str = "",
    enterprise_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """岗位列表（分页 + 名称搜索 + 按企业筛选，含企业名）。"""
    q = db.query(Job, Enterprise.name).join(Enterprise, Job.enterprise_id == Enterprise.id)
    if keyword:
        q = q.filter(Job.title.contains(keyword))
    if enterprise_id is not None:
        q = q.filter(Job.enterprise_id == enterprise_id)
    total = q.count()
    rows = q.order_by(Job.id).offset((page - 1) * size).limit(size).all()
    items = [
        {
            "id": j.id,
            "enterprise_id": j.enterprise_id,
            "enterprise_name": ename,
            "title": j.title,
            "description": j.description,
            "requirements": j.requirements,
            "skills": j.skills,
            "created_at": _iso(j.created_at),
        }
        for j, ename in rows
    ]
    return ok({"items": items, "total": total, "page": page, "size": size})


@router.post("/jobs")
def create_job(body: JobCreate, db: Session = Depends(get_db)):
    """新建岗位（校验所属企业存在）。"""
    if db.get(Enterprise, body.enterprise_id) is None:
        return fail(1002, "所属企业不存在")
    job = Job(**body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return ok(
        {
            "id": job.id,
            "enterprise_id": job.enterprise_id,
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
            "skills": job.skills,
            "created_at": _iso(job.created_at),
        }
    )


# ============ 候选人 ============


@router.get("/candidates")
def list_candidates(
    keyword: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """候选人列表（分页 + 姓名/邮箱模糊搜索）。"""
    q = db.query(Candidate)
    if keyword:
        q = q.filter(Candidate.name.contains(keyword) | Candidate.email.contains(keyword))
    total = q.count()
    rows = q.order_by(Candidate.id).offset((page - 1) * size).limit(size).all()
    items = [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "status": c.status,
            "created_at": _iso(c.created_at),
        }
        for c in rows
    ]
    return ok({"items": items, "total": total, "page": page, "size": size})


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """候选人详情（含简历解析画像）。"""
    c = db.get(Candidate, candidate_id)
    if c is None:
        return fail(1002, "候选人不存在")
    return ok(_candidate_dict(c))


@router.put("/candidates/{candidate_id}")
def update_candidate(candidate_id: int, body: CandidateUpdate, db: Session = Depends(get_db)):
    """更新候选人（仅更新传入的非空字段）。"""
    c = db.get(Candidate, candidate_id)
    if c is None:
        return fail(1002, "候选人不存在")
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    for k, v in updates.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return ok(_candidate_dict(c))


def _candidate_dict(c: Candidate) -> dict:
    """候选人序列化：profile_json 解析为 profile 字段。"""
    profile: dict = {}
    if c.profile_json:
        try:
            profile = json.loads(c.profile_json)
        except json.JSONDecodeError:
            profile = {}
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "resume_file": c.resume_file,
        "status": c.status,
        "profile": profile,
        "created_at": _iso(c.created_at),
    }
