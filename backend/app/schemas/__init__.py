"""Pydantic 请求/响应模型（成员B维护）。

统一响应格式约定：
    { "code": 0, "message": "success", "data": { ... } }
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

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
