"""面试官（HR/教师/管理员）模型（成员B维护）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Interviewer(Base):
    """面试官：后台"面试官管理"业务对象。"""

    __tablename__ = "interviewers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), default="")
    role: Mapped[str] = mapped_column(String(20), default="hr")  # hr / teacher / admin
    title: Mapped[str] = mapped_column(String(50), default="")  # 职称/职位
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Interviewer {self.id} {self.name}>"
