"""Problem catalog API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProblemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    difficulty: str
    time_limit_ms: int
    memory_limit_mb: int


class SampleTestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    input_data: str
    expected_output: str


class ProblemDetail(ProblemSummary):
    description: str
    sample_test_cases: list[SampleTestCaseRead]


class ProblemListResponse(BaseModel):
    items: list[ProblemSummary]
    offset: int
    limit: int
    total: int
