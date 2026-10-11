"""Database queries for published problems."""

from uuid import UUID

from backend.models import Problem
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class ProblemsRepository:
    async def list_published(
        self, session: AsyncSession, *, offset: int, limit: int
    ) -> tuple[list[Problem], int]:
        query = select(Problem).where(Problem.is_published.is_(True)).order_by(Problem.title)
        items = list((await session.scalars(query.offset(offset).limit(limit))).all())
        total = await session.scalar(
            select(func.count()).select_from(Problem).where(Problem.is_published.is_(True))
        )
        return items, total or 0

    async def get_published_by_id(self, session: AsyncSession, problem_id: UUID) -> Problem | None:
        query = (
            select(Problem)
            .where(Problem.id == problem_id, Problem.is_published.is_(True))
            .options(selectinload(Problem.test_cases))
        )
        return await session.scalar(query)
