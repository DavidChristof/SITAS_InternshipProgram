"""岗位模型（成员B维护）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Job(Base):
    """岗位：后台"岗位管理"业务对象，也是 RAG 知识库中岗位 JD 的源头。"""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    enterprise_id: Mapped[int] = mapped_column(ForeignKey("enterprises.id"), index=True)
    title: Mapped[str] = mapped_column(String(100), index=True)  # 岗位名称
    description: Mapped[str] = mapped_column(Text, default="")  # 岗位 JD 全文
    requirements: Mapped[str] = mapped_column(Text, default="")  # 任职要求
    skills: Mapped[str] = mapped_column(Text, default="")  # 技能关键词，逗号分隔
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    enterprise: Mapped["Enterprise"] = relationship(back_populates="jobs")

    def __repr__(self) -> str:
        return f"<Job {self.id} {self.title}>"
