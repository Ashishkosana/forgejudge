"""Problem catalog endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.problems import (
    ProblemDetail,
    ProblemListResponse,
    ProblemSummary,
    SampleTestCaseRead,
)
from backend.common.database import get_session
from backend.services.problems import ProblemNotFoundError, ProblemsService

router = APIRouter(prefix="/problems", tags=["problems"])
problems_service = ProblemsService()


@router.get("", response_model=ProblemListResponse)
async def list_problems(
    session: Annotated[AsyncSession, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProblemListResponse:
    items, total = await problems_service.list_published(session, offset=offset, limit=limit)
    return ProblemListResponse(
        items=[ProblemSummary.model_validate(problem) for problem in items],
        offset=offset,
        limit=limit,
        total=total,
    )


@router.get("/{problem_id}", response_model=ProblemDetail)
async def get_problem(
    problem_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProblemDetail:
    try:
        problem = await problems_service.get_published(session, problem_id)
    except ProblemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        ) from exc

    return ProblemDetail(
        **ProblemSummary.model_validate(problem).model_dump(),
        description=problem.description,
        sample_test_cases=[
            SampleTestCaseRead.model_validate(test_case)
            for test_case in problem.test_cases
            if test_case.is_sample
        ],
    )
