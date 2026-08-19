"""HR/教师/管理员 后台管理 API（成员B实现，成员C前端调用）。

接口契约（成员C依赖）：
    企业：     GET/POST/PUT/DELETE /api/admin/enterprises[/{id}]
    岗位：     GET/POST/PUT/DELETE /api/admin/jobs[/{id}]
    候选人：   GET/PUT /api/admin/candidates[/{id}]
    面试官：   GET/POST/PUT/DELETE /api/admin/interviewers[/{id}]
    题库：     GET/POST/PUT/DELETE /api/admin/questions[/{id}]
    面试记录： GET /api/admin/interviews[/{id}]   （可筛选 candidate_id/job_id/status）

分页约定：GET 列表接口支持 ?page=1&size=10（page 从 1 起，size 默认 10、上限 100），
         返回 data = {"list": [...], "total": N, "page": 1, "size": 10}
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Candidate,
    Enterprise,
    Interview,
    InterviewAnswer,
    Interviewer,
    Job,
    Question,
)
from ..schemas import (
    CandidateCreate,
    CandidateUpdate,
    EnterpriseCreate,
    EnterpriseUpdate,
    InterviewerCreate,
    InterviewerUpdate,
    JobCreate,
    JobUpdate,
    QuestionCreate,
    QuestionUpdate,
    fail,
    ok,
)

router = APIRouter(prefix="/api/admin", tags=["后台管理"])


def _iso(dt) -> str | None:
    """datetime → ISO 字符串（可空）。"""
    return dt.isoformat() if dt else None


def _enterprise_dict(e: Enterprise) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "industry": e.industry,
        "description": e.description,
        "created_at": _iso(e.created_at),
    }


def _job_dict(j: Job) -> dict:
    return {
        "id": j.id,
        "enterprise_id": j.enterprise_id,
        "title": j.title,
        "description": j.description,
        "requirements": j.requirements,
        "skills": j.skills,
        "created_at": _iso(j.created_at),
    }


def _interviewer_dict(i: Interviewer) -> dict:
    return {
        "id": i.id,
        "name": i.name,
        "role": i.role,
        "title": i.title,
        "created_at": _iso(i.created_at),
    }


def _question_dict(q: Question) -> dict:
    return {
        "id": q.id,
        "job_id": q.job_id,
        "category": q.category,
        "question": q.question,
        "expected_points": q.expected_points,
        "sample_answer": q.sample_answer,
        "difficulty": q.difficulty,
        "created_at": _iso(q.created_at),
    }


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
    return ok({"list": [_enterprise_dict(e) for e in rows], "total": total, "page": page, "size": size})


@router.post("/enterprises")
def create_enterprise(body: EnterpriseCreate, db: Session = Depends(get_db)):
    """新建企业。"""
    ent = Enterprise(**body.model_dump())
    db.add(ent)
    db.commit()
    db.refresh(ent)
    return ok(_enterprise_dict(ent))


@router.get("/enterprises/{enterprise_id}")
def get_enterprise(enterprise_id: int, db: Session = Depends(get_db)):
    """企业详情。"""
    e = db.get(Enterprise, enterprise_id)
    if e is None:
        return fail(1002, "企业不存在")
    return ok(_enterprise_dict(e))


@router.put("/enterprises/{enterprise_id}")
def update_enterprise(enterprise_id: int, body: EnterpriseUpdate, db: Session = Depends(get_db)):
    """更新企业（仅更新传入的非空字段）。"""
    e = db.get(Enterprise, enterprise_id)
    if e is None:
        return fail(1002, "企业不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return ok(_enterprise_dict(e))


@router.delete("/enterprises/{enterprise_id}")
def delete_enterprise(enterprise_id: int, db: Session = Depends(get_db)):
    """删除企业（有岗位时拒绝）。"""
    e = db.get(Enterprise, enterprise_id)
    if e is None:
        return fail(1002, "企业不存在")
    if db.query(Job).filter(Job.enterprise_id == enterprise_id).count():
        return fail(1001, "该企业下还有岗位，请先删除岗位")
    db.delete(e)
    db.commit()
    return ok({"deleted": enterprise_id})


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
    items = []
    for j, ename in rows:
        d = _job_dict(j)
        d["enterprise_name"] = ename
        items.append(d)
    return ok({"list": items, "total": total, "page": page, "size": size})


@router.post("/jobs")
def create_job(body: JobCreate, db: Session = Depends(get_db)):
    """新建岗位（校验所属企业存在）。"""
    if db.get(Enterprise, body.enterprise_id) is None:
        return fail(1002, "所属企业不存在")
    job = Job(**body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return ok(_job_dict(job))


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    """岗位详情（含企业名）。"""
    j = db.get(Job, job_id)
    if j is None:
        return fail(1002, "岗位不存在")
    d = _job_dict(j)
    ent = db.get(Enterprise, j.enterprise_id)
    d["enterprise_name"] = ent.name if ent else ""
    return ok(d)


@router.put("/jobs/{job_id}")
def update_job(job_id: int, body: JobUpdate, db: Session = Depends(get_db)):
    """更新岗位（仅更新传入的非空字段）。"""
    j = db.get(Job, job_id)
    if j is None:
        return fail(1002, "岗位不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(j, k, v)
    db.commit()
    db.refresh(j)
    return ok(_job_dict(j))


@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """删除岗位（连同其题库题目）。"""
    j = db.get(Job, job_id)
    if j is None:
        return fail(1002, "岗位不存在")
    db.query(Question).filter(Question.job_id == job_id).delete(synchronize_session=False)
    db.delete(j)
    db.commit()
    return ok({"deleted": job_id})


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
    return ok({"list": items, "total": total, "page": page, "size": size})


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
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return ok(_candidate_dict(c))


@router.post("/candidates")
def create_candidate(body: CandidateCreate, db: Session = Depends(get_db)):
    """新建候选人（后台手动新增）。"""
    cand = Candidate(**body.model_dump())
    db.add(cand)
    db.commit()
    db.refresh(cand)
    return ok(_candidate_dict(cand))


@router.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """删除候选人（已有面试记录时拒绝）。"""
    c = db.get(Candidate, candidate_id)
    if c is None:
        return fail(1002, "候选人不存在")
    if db.query(Interview).filter(Interview.candidate_id == candidate_id).count():
        return fail(1001, "该候选人已有面试记录，无法删除")
    db.delete(c)
    db.commit()
    return ok({"deleted": candidate_id})


# ============ 面试官 ============


@router.get("/interviewers")
def list_interviewers(
    keyword: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """面试官列表（分页 + 姓名模糊搜索）。"""
    q = db.query(Interviewer)
    if keyword:
        q = q.filter(Interviewer.name.contains(keyword))
    total = q.count()
    rows = q.order_by(Interviewer.id).offset((page - 1) * size).limit(size).all()
    return ok({"list": [_interviewer_dict(i) for i in rows], "total": total, "page": page, "size": size})


@router.post("/interviewers")
def create_interviewer(body: InterviewerCreate, db: Session = Depends(get_db)):
    """新建面试官。"""
    iv = Interviewer(**body.model_dump())
    db.add(iv)
    db.commit()
    db.refresh(iv)
    return ok(_interviewer_dict(iv))


@router.get("/interviewers/{interviewer_id}")
def get_interviewer(interviewer_id: int, db: Session = Depends(get_db)):
    """面试官详情。"""
    i = db.get(Interviewer, interviewer_id)
    if i is None:
        return fail(1002, "面试官不存在")
    return ok(_interviewer_dict(i))


@router.put("/interviewers/{interviewer_id}")
def update_interviewer(interviewer_id: int, body: InterviewerUpdate, db: Session = Depends(get_db)):
    """更新面试官（仅更新传入的非空字段）。"""
    i = db.get(Interviewer, interviewer_id)
    if i is None:
        return fail(1002, "面试官不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(i, k, v)
    db.commit()
    db.refresh(i)
    return ok(_interviewer_dict(i))


@router.delete("/interviewers/{interviewer_id}")
def delete_interviewer(interviewer_id: int, db: Session = Depends(get_db)):
    """删除面试官（已有面试记录时拒绝）。"""
    i = db.get(Interviewer, interviewer_id)
    if i is None:
        return fail(1002, "面试官不存在")
    if db.query(Interview).filter(Interview.interviewer_id == interviewer_id).count():
        return fail(1001, "该面试官已有面试记录，无法删除")
    db.delete(i)
    db.commit()
    return ok({"deleted": interviewer_id})


# ============ 题库 ============


@router.get("/questions")
def list_questions(
    keyword: str = "",
    job_id: int | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """题库列表（分页 + 按岗位/环节筛选 + 题目模糊搜索）。"""
    q = db.query(Question)
    if keyword:
        q = q.filter(Question.question.contains(keyword))
    if job_id is not None:
        q = q.filter(Question.job_id == job_id)
    if category:
        q = q.filter(Question.category == category)
    total = q.count()
    rows = q.order_by(Question.id).offset((page - 1) * size).limit(size).all()
    return ok({"list": [_question_dict(q) for q in rows], "total": total, "page": page, "size": size})


@router.post("/questions")
def create_question(body: QuestionCreate, db: Session = Depends(get_db)):
    """新建题库题目。"""
    q = Question(**body.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return ok(_question_dict(q))


@router.get("/questions/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db)):
    """题库题目详情。"""
    q = db.get(Question, question_id)
    if q is None:
        return fail(1002, "题目不存在")
    return ok(_question_dict(q))


@router.put("/questions/{question_id}")
def update_question(question_id: int, body: QuestionUpdate, db: Session = Depends(get_db)):
    """更新题库题目（仅更新传入的非空字段）。"""
    q = db.get(Question, question_id)
    if q is None:
        return fail(1002, "题目不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(q, k, v)
    db.commit()
    db.refresh(q)
    return ok(_question_dict(q))


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    """删除题库题目。"""
    q = db.get(Question, question_id)
    if q is None:
        return fail(1002, "题目不存在")
    db.delete(q)
    db.commit()
    return ok({"deleted": question_id})


# ============ 面试记录 ============


def _interview_report(iv: Interview) -> dict:
    """解析面试记录的 report_json。"""
    if iv.report_json:
        try:
            return json.loads(iv.report_json)
        except json.JSONDecodeError:
            return {}
    return {}


@router.get("/interviews")
def list_interviews(
    candidate_id: int | None = None,
    job_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """面试记录列表（分页 + 按候选人/岗位/状态筛选，含候选人名与岗位名）。"""
    q = (
        db.query(Interview, Job.title, Candidate.name)
        .join(Job, Interview.job_id == Job.id)
        .join(Candidate, Interview.candidate_id == Candidate.id)
    )
    if candidate_id is not None:
        q = q.filter(Interview.candidate_id == candidate_id)
    if job_id is not None:
        q = q.filter(Interview.job_id == job_id)
    if status:
        q = q.filter(Interview.status == status)
    total = q.count()
    rows = q.order_by(Interview.id.desc()).offset((page - 1) * size).limit(size).all()
    items = [
        {
            "id": iv.id,
            "candidate_id": iv.candidate_id,
            "candidate_name": cname,
            "job_id": iv.job_id,
            "job_title": jtitle,
            "status": iv.status,
            "current_round": iv.current_round,
            "total_score": _interview_report(iv).get("total_score"),
            "created_at": _iso(iv.created_at),
        }
        for iv, jtitle, cname in rows
    ]
    return ok({"list": items, "total": total, "page": page, "size": size})


@router.get("/interviews/{interview_id}")
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    """面试记录详情（含逐题问答）。"""
    iv = db.get(Interview, interview_id)
    if iv is None:
        return fail(1002, "面试不存在")
    job = db.get(Job, iv.job_id)
    candidate = db.get(Candidate, iv.candidate_id)
    answers = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.interview_id == iv.id)
        .order_by(InterviewAnswer.round_no)
        .all()
    )
    return ok(
        {
            "id": iv.id,
            "candidate_id": iv.candidate_id,
            "candidate_name": candidate.name if candidate else "",
            "job_id": iv.job_id,
            "job_title": job.title if job else "",
            "status": iv.status,
            "current_round": iv.current_round,
            "started_at": _iso(iv.started_at),
            "created_at": _iso(iv.created_at),
            "report": _interview_report(iv),
            "answers": [
                {
                    "id": a.id,
                    "round_no": a.round_no,
                    "category": a.category,
                    "question": a.question,
                    "expected_points": a.expected_points,
                    "answer_text": a.answer_text,
                    "audio_url": a.audio_url,
                    "score": a.score,
                    "feedback": a.feedback,
                }
                for a in answers
            ],
        }
    )
