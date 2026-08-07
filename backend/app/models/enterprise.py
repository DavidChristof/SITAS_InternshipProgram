"""企业模型（成员B维护）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Enterprise(Base):
    """企业：后台"企业管理"业务对象。"""

    __tablename__ = "enterprises"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)  # 企业名称
    industry: Mapped[str] = mapped_column(String(50), default="")  # 所属行业
    description: Mapped[str] = mapped_column(Text, default="")  # 企业简介
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship(back_populates="enterprise")

    def __repr__(self) -> str:
        return f"<Enterprise {self.id} {self.name}>"
