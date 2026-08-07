"""HR/教师/管理员 后台管理 API（成员B实现，成员C前端调用）。

接口契约（成员C依赖）：
    企业：     GET/POST/PUT/DELETE /api/admin/enterprises[/{id}]
    岗位：     GET/POST/PUT/DELETE /api/admin/jobs[/{id}]
    候选人：   GET/PUT /api/admin/candidates[/{id}]
    面试官：   GET/POST/PUT/DELETE /api/admin/interviewers[/{id}]
    题库：     GET/POST/PUT/DELETE /api/admin/questions[/{id}]
    面试记录： GET /api/admin/interviews   （可筛选 candidate_id/job_id/status）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import fail, ok

router = APIRouter(prefix="/api/admin", tags=["后台管理"])


@router.get("/ping")
def ping():
    """占位示例：验证路由连通。"""
    return ok({"pong": True})
