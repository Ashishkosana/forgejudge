"""Submission creation and retrieval use cases."""

from uuid import UUID

from backend.models import OutboxEvent, Submission
from backend.repositories.problems import ProblemsRepository
from backend.repositories.submissions import SubmissionsRepository
from backend.services.problems import ProblemNotFoundError
from sqlalchemy.ext.asyncio import AsyncSession


class SubmissionsService:
    def __init__(
        self,
        submissions: SubmissionsRepository | None = None,
        problems: ProblemsRepository | None = None,
    ) -> None:
        self.submissions = submissions or SubmissionsRepository()
        self.problems = problems or ProblemsRepository()

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        problem_id: UUID,
        source_code: str,
        language: str,
    ) -> Submission:
        problem = await self.problems.get_published_by_id(session, problem_id)
        if problem is None:
            raise ProblemNotFoundError

        submission = Submission(
            user_id=user_id,
            problem_id=problem.id,
            language=language,
            source_code=source_code,
        )
        session.add(submission)
        await session.flush()
        event = OutboxEvent(
            event_type="submission.created",
            aggregate_id=submission.id,
            payload={"submission_id": str(submission.id)},
        )
        session.add(event)
        await session.commit()
        refreshed = await self.submissions.get_by_id(session, submission.id)
        if refreshed is None:
            raise RuntimeError("Committed submission disappeared before response serialization")
        return refreshed

    async def get(self, session: AsyncSession, submission_id: UUID) -> Submission | None:
        return await self.submissions.get_by_id(session, submission_id)

    async def list(
        self,
        session: AsyncSession,
        *,
        offset: int,
        limit: int,
        problem_id: UUID | None,
        user_id: UUID | None = None,
    ) -> tuple[list[Submission], int]:
        return await self.submissions.list_for_problem(
            session, offset=offset, limit=limit, problem_id=problem_id, user_id=user_id
        )
