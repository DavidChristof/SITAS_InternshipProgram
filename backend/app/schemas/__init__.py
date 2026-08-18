"""Pydantic 请求/响应模型（成员B维护）。

统一响应格式约定：
    { "code": 0, "message": "success", "data": { ... } }
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None


def ok(data: Any = None, message: str = "success") -> ApiResponse:
    """成功响应。示例：return ok({"list": items})"""
    return ApiResponse(code=0, message=message, data=data)


def fail(code: int, message: str, data: Any = None) -> ApiResponse:
    """失败响应。业务错误码约定：1001 参数错误 / 1002 资源未找到 / 1003 服务器内部错误。"""
    return ApiResponse(code=code, message=message, data=data)


# ============ 请求模型（成员B 维护，供 POST/PUT 请求体校验）============


class EnterpriseCreate(BaseModel):
    """新建企业请求体。"""

    name: str = Field(min_length=1, max_length=100, description="企业名称")
    industry: str = ""
    description: str = ""


class EnterpriseUpdate(BaseModel):
    """更新企业请求体（全部可选，仅更新非空字段）。"""

    name: str | None = None
    industry: str | None = None
    description: str | None = None


class JobCreate(BaseModel):
    """新建岗位请求体。"""

    enterprise_id: int = Field(..., description="所属企业 id")
    title: str = Field(min_length=1, max_length=100, description="岗位名称")
    description: str = ""
    requirements: str = ""
    skills: str = ""


class JobUpdate(BaseModel):
    """更新岗位请求体（全部可选，仅更新非空字段）。"""

    enterprise_id: int | None = None
    title: str | None = None
    description: str | None = None
    requirements: str | None = None
    skills: str | None = None


class CandidateUpdate(BaseModel):
    """更新候选人请求体（全部可选，仅更新非空字段）。"""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None


class InterviewerCreate(BaseModel):
    """新建面试官请求体。"""

    name: str = Field(min_length=1, max_length=50)
    role: str = "hr"  # hr / teacher / admin
    title: str = ""


class InterviewerUpdate(BaseModel):
    """更新面试官请求体（全部可选，仅更新非空字段）。"""

    name: str | None = None
    role: str | None = None
    title: str | None = None


class QuestionCreate(BaseModel):
    """新建题库题目请求体。"""

    job_id: int | None = None  # None 表示通用题
    category: str = "technical"  # self_intro/project/technical/behavioral/reverse
    question: str = Field(min_length=1)
    expected_points: str = ""
    sample_answer: str = ""
    difficulty: int = Field(2, ge=1, le=5)


class QuestionUpdate(BaseModel):
    """更新题库题目请求体（全部可选，仅更新非空字段）。"""

    job_id: int | None = None
    category: str | None = None
    question: str | None = None
    expected_points: str | None = None
    sample_answer: str | None = None
    difficulty: int | None = None


class InterviewCreate(BaseModel):
    """候选人创建一场面试请求体。"""

    candidate_id: int
    job_id: int
