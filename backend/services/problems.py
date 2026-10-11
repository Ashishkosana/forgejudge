"""Problem catalog use cases."""

from uuid import UUID

from backend.models import Problem
from backend.repositories.problems import ProblemsRepository
from sqlalchemy.ext.asyncio import AsyncSession


class ProblemNotFoundError(Exception):
    """Raised when a published problem does not exist."""


class ProblemsService:
    def __init__(self, repository: ProblemsRepository | None = None) -> None:
        self.repository = repository or ProblemsRepository()

    async def list_published(
        self, session: AsyncSession, *, offset: int, limit: int
    ) -> tuple[list[Problem], int]:
        return await self.repository.list_published(session, offset=offset, limit=limit)

    async def get_published(self, session: AsyncSession, problem_id: UUID) -> Problem:
        problem = await self.repository.get_published_by_id(session, problem_id)
        if problem is None:
            raise ProblemNotFoundError
        return problem
