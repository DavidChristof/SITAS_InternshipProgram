"""候选人（学生）模型（成员B维护）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Candidate(Base):
    """候选人：候选人端用户，后台"候选人管理"业务对象。"""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    resume_text: Mapped[str] = mapped_column(Text, default="")  # 简历原文（解析前）
    resume_file: Mapped[str] = mapped_column(String(200), default="")  # 简历文件路径
    profile_json: Mapped[str] = mapped_column(Text, default="")  # 简历解析结果 JSON 串
    status: Mapped[str] = mapped_column(String(20), default="active")  # active / closed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Candidate {self.id} {self.name}>"
