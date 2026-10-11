"""Administrative operations protected by the current database role."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import require_admin
from backend.api.schemas.auth import UserRead
from backend.common.database import get_session
from backend.models.user import User

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/users", response_model=list[UserRead])
async def list_users(
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[UserRead]:
    users = await session.scalars(select(User).order_by(User.created_at, User.id).limit(100))
    return [UserRead.model_validate(user) for user in users]
