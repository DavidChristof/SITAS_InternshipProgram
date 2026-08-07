"""候选人端 API（成员B实现，成员C前端调用）。

接口契约（成员C依赖，请保持路径/参数不变，改动需通知C）：
    POST /api/candidate/resume             上传简历（multipart，字段 file）→ 解析并返回候选人档案
    GET  /api/candidate/jobs               可投递岗位列表（含企业名）
    POST /api/candidate/interview          创建一场面试（body: {candidate_id, job_id}）→ 返回 interview_id
    GET  /api/candidate/interviews         我的面试历史（含状态、总分）
    GET  /api/candidate/interview/{id}     面试详情（逐题问答+评分+报告）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import fail, ok

router = APIRouter(prefix="/api/candidate", tags=["候选人端"])


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    """示例实现：岗位列表（成员B 扩展为带企业名/分页/搜索）。"""
    from ..models import Job

    jobs = db.query(Job).order_by(Job.id).limit(50).all()
    data = [
        {"id": j.id, "title": j.title, "skills": j.skills, "description": j.description}
        for j in jobs
    ]
    return ok(data)
