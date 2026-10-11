"""Per-test-case outcome and execution measurements."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.submission import Submission
    from backend.models.test_case import TestCase


class SubmissionResult(TimestampMixin, Base):
    __tablename__ = "submission_results"
    __table_args__ = (
        UniqueConstraint("submission_id", "test_case_id", name="uq_result_submission_test_case"),
        CheckConstraint(
            "status IN ('NOT_EVALUATED', 'ACCEPTED', 'WRONG_ANSWER', 'RUNTIME_ERROR', "
            "'TIME_LIMIT_EXCEEDED', 'MEMORY_LIMIT_EXCEEDED')",
            name="ck_submission_results_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NOT_EVALUATED", server_default="NOT_EVALUATED"
    )
    runtime_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission: Mapped[Submission] = relationship(back_populates="results")
    test_case: Mapped[TestCase] = relationship(back_populates="results")
