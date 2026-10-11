"""Submission request and response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.api.schemas.problems import ProblemSummary
from backend.models.enums import SubmissionStatus, SubmissionVerdict


class SubmissionCreate(BaseModel):
    problem_id: UUID
    source_code: str = Field(min_length=1, max_length=100_000)
    language: Literal["python"] = "python"


class SubmissionResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    test_case_id: UUID
    status: SubmissionVerdict
    runtime_ms: float | None
    memory_kb: int | None
    stdout: str | None
    stderr: str | None


class SubmissionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    problem_id: UUID
    problem: ProblemSummary
    language: str
    status: SubmissionStatus
    verdict: SubmissionVerdict
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class SubmissionDetail(SubmissionSummary):
    user_id: UUID | None
    source_code: str
    failure_reason: str | None
    results: list[SubmissionResultRead]


class SubmissionListResponse(BaseModel):
    items: list[SubmissionSummary]
    offset: int
    limit: int
    total: int
