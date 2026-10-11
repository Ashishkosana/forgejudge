"""Problem input/output cases; only samples are exposed by the public API."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.problem import Problem
    from backend.models.submission_result import SubmissionResult


class TestCase(TimestampMixin, Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("problem_id", "position", name="uq_test_cases_problem_position"),
        CheckConstraint("position >= 0", name="ck_test_cases_position_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    problem_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_sample: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    problem: Mapped[Problem] = relationship(back_populates="test_cases")
    results: Mapped[list[SubmissionResult]] = relationship(back_populates="test_case")
