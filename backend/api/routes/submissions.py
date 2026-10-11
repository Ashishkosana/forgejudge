"""Submission creation and status endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.submissions import (
    SubmissionCreate,
    SubmissionDetail,
    SubmissionListResponse,
    SubmissionSummary,
)
from backend.common.database import get_session
from backend.services.problems import ProblemNotFoundError
from backend.services.submissions import SubmissionsService

router = APIRouter(prefix="/submissions", tags=["submissions"])
submissions_service = SubmissionsService()


@router.post("", response_model=SubmissionDetail, status_code=status.HTTP_202_ACCEPTED)
async def create_submission(
    payload: SubmissionCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubmissionDetail:
    try:
        submission = await submissions_service.create(
            session,
            problem_id=payload.problem_id,
            source_code=payload.source_code,
            language=payload.language,
        )
    except ProblemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found"
        ) from exc
    return SubmissionDetail.model_validate(submission)


@router.get("", response_model=SubmissionListResponse)
async def list_submissions(
    session: Annotated[AsyncSession, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    problem_id: UUID | None = None,
) -> SubmissionListResponse:
    items, total = await submissions_service.list(
        session,
        offset=offset,
        limit=limit,
        problem_id=problem_id,
    )
    return SubmissionListResponse(
        items=[SubmissionSummary.model_validate(item) for item in items],
        offset=offset,
        limit=limit,
        total=total,
    )


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def get_submission(
    submission_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubmissionDetail:
    submission = await submissions_service.get(session, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return SubmissionDetail.model_validate(submission)
