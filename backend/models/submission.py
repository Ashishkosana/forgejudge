"""Submitted source and asynchronous processing state."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin
from backend.models.enums import SubmissionStatus, SubmissionVerdict

if TYPE_CHECKING:
    from backend.models.problem import Problem
    from backend.models.submission_result import SubmissionResult
    from backend.models.user import User


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED')", name="ck_submissions_status"
        ),
        CheckConstraint(
            "verdict IN ('NOT_EVALUATED', 'ACCEPTED', 'WRONG_ANSWER', 'RUNTIME_ERROR', "
            "'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED')",
            name="ck_submissions_verdict",
        ),
        Index("ix_submissions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    problem_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("problems.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=SubmissionStatus.QUEUED.value,
        server_default=SubmissionStatus.QUEUED.value,
        index=True,
    )
    verdict: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SubmissionVerdict.NOT_EVALUATED.value,
        server_default=SubmissionVerdict.NOT_EVALUATED.value,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship(back_populates="submissions")
    problem: Mapped[Problem] = relationship(back_populates="submissions")
    results: Mapped[list[SubmissionResult]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="SubmissionResult.created_at",
    )
