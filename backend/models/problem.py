"""Coding problem metadata and resource limits."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.submission import Submission
    from backend.models.test_case import TestCase


class Problem(TimestampMixin, Base):
    __tablename__ = "problems"
    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_problems_difficulty"),
        CheckConstraint("time_limit_ms > 0", name="ck_problems_time_limit_positive"),
        CheckConstraint("memory_limit_mb > 0", name="ck_problems_memory_limit_positive"),
        Index("ix_problems_published_title", "is_published", "title"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    time_limit_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1000, server_default="1000"
    )
    memory_limit_mb: Mapped[int] = mapped_column(
        Integer, nullable=False, default=128, server_default="128"
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    test_cases: Mapped[list[TestCase]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="TestCase.position"
    )
    submissions: Mapped[list[Submission]] = relationship(back_populates="problem")
