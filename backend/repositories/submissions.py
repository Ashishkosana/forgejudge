"""Database queries and state transitions for submissions."""

from datetime import UTC, datetime
from uuid import UUID

from backend.models import Problem, Submission, SubmissionResult
from backend.models.enums import SubmissionStatus, SubmissionVerdict
from backend.models.judging import CaseResult
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class SubmissionsRepository:
    async def get_by_id(self, session: AsyncSession, submission_id: UUID) -> Submission | None:
        query = (
            select(Submission)
            .where(Submission.id == submission_id)
            .options(selectinload(Submission.problem), selectinload(Submission.results))
        )
        return await session.scalar(query)

    async def list_for_problem(
        self,
        session: AsyncSession,
        *,
        offset: int,
        limit: int,
        problem_id: UUID | None,
    ) -> tuple[list[Submission], int]:
        filters = [Submission.problem_id == problem_id] if problem_id else []
        query = (
            select(Submission)
            .where(*filters)
            .options(selectinload(Submission.problem))
            .order_by(Submission.created_at.desc(), Submission.id)
        )
        items = list((await session.scalars(query.offset(offset).limit(limit))).all())
        total = await session.scalar(select(func.count()).select_from(Submission).where(*filters))
        return items, total or 0

    async def mark_running(self, session: AsyncSession, submission_id: UUID) -> bool:
        result = await session.execute(
            update(Submission)
            .where(
                Submission.id == submission_id,
                Submission.status == SubmissionStatus.QUEUED.value,
            )
            .values(
                status=SubmissionStatus.RUNNING.value,
                started_at=func.now(),
                updated_at=func.now(),
            )
            .returning(Submission.id)
        )
        return result.scalar_one_or_none() is not None

    async def get_for_processing(
        self, session: AsyncSession, submission_id: UUID
    ) -> Submission | None:
        query = (
            select(Submission)
            .where(Submission.id == submission_id)
            .options(
                selectinload(Submission.problem).selectinload(Problem.test_cases),
                selectinload(Submission.results),
            )
            .with_for_update(of=Submission)
        )
        return await session.scalar(query)

    async def complete_with_evaluation(
        self,
        session: AsyncSession,
        submission: Submission,
        case_results: list[CaseResult],
        verdict: SubmissionVerdict,
    ) -> None:
        existing_results = {result.test_case_id: result for result in submission.results}
        for case_result in case_results:
            result = existing_results.get(case_result.test_case_id)
            if result is None:
                result = SubmissionResult(
                    submission_id=submission.id,
                    test_case_id=case_result.test_case_id,
                )
                session.add(result)
            result.status = case_result.verdict.value
            result.runtime_ms = case_result.runtime_ms
            result.memory_kb = case_result.memory_kb
            result.stdout = case_result.stdout
            result.stderr = case_result.stderr

        submission.status = SubmissionStatus.COMPLETED.value
        submission.verdict = verdict.value
        submission.completed_at = datetime.now(UTC)
        submission.updated_at = datetime.now(UTC)

    async def mark_failed(self, session: AsyncSession, submission_id: UUID, reason: str) -> bool:
        result = await session.execute(
            update(Submission)
            .where(
                Submission.id == submission_id,
                Submission.status.in_(
                    [SubmissionStatus.QUEUED.value, SubmissionStatus.RUNNING.value]
                ),
            )
            .values(
                status=SubmissionStatus.FAILED.value,
                failure_reason=reason[:2000],
                completed_at=func.now(),
                updated_at=func.now(),
            )
            .returning(Submission.id)
        )
        return result.scalar_one_or_none() is not None
