"""面试题库模型（成员B维护）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Question(Base):
    """面试题库：后台"题库管理"业务对象，也是 RAG 知识库的一部分。"""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id"), index=True, nullable=True
    )  # 关联岗位，None 表示通用题
    category: Mapped[str] = mapped_column(
        String(30), default="technical"
    )  # self_intro / project / technical / behavioral / reverse
    question: Mapped[str] = mapped_column(Text)  # 题目
    expected_points: Mapped[str] = mapped_column(Text, default="")  # 评分要点，逗号分隔
    sample_answer: Mapped[str] = mapped_column(Text, default="")  # 优秀回答样例
    difficulty: Mapped[int] = mapped_column(Integer, default=2)  # 1-5
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Question {self.id} [{self.category}] {self.question[:20]}>"
