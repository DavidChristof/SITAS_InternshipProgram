"""面试记录模型（成员B维护）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Interview(Base):
    """一场面试记录：面试流程状态机由成员A/B协商、成员B落地。"""

    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    interviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("interviewers.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/finished
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    report_json: Mapped[str] = mapped_column(Text, default="")  # 面试报告 JSON 串
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    answers: Mapped[list["InterviewAnswer"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Interview {self.id} candidate={self.candidate_id} status={self.status}>"


class InterviewAnswer(Base):
    """单道题的问答与评分记录。"""

    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    round_no: Mapped[int] = mapped_column(Integer, default=1)  # 第几轮
    category: Mapped[str] = mapped_column(String(30), default="")  # 环节类型
    question: Mapped[str] = mapped_column(Text)  # 面试官问题
    answer_text: Mapped[str] = mapped_column(Text, default="")  # 候选人回答
    audio_url: Mapped[str] = mapped_column(String(200), default="")  # 语音回答文件路径
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 单题评分 0-100
    feedback: Mapped[str] = mapped_column(Text, default="")  # 单题反馈
    evidence: Mapped[str] = mapped_column(Text, default="")  # RAG 检索依据 JSON 串
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    interview: Mapped["Interview"] = relationship(back_populates="answers")

    def __repr__(self) -> str:
        return f"<InterviewAnswer {self.id} round={self.round_no}>"
