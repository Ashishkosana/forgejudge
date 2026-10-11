"""Immutable inputs and outcomes used by the judge worker."""

from dataclasses import dataclass
from uuid import UUID

from backend.models.enums import SubmissionVerdict


@dataclass(frozen=True, slots=True)
class TestCaseInput:
    id: UUID
    input_data: str
    expected_output: str


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    verdict: SubmissionVerdict
    runtime_ms: float | None
    memory_kb: int | None
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class CaseResult(ExecutionResult):
    test_case_id: UUID
