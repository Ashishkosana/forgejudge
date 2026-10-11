"""Authentication lifecycle checks against an explicitly configured test database."""

from __future__ import annotations

import hashlib
import os
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from backend.models import Base, RefreshSession
from backend.services.authentication import (
    AuthenticationService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def auth_session() -> AsyncIterator[AsyncSession]:
    database_url = os.environ.get("FORGEJUDGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set FORGEJUDGE_TEST_DATABASE_URL to run PostgreSQL auth integration tests")

    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _unique_email() -> str:
    return f"auth-{secrets.token_hex(12)}@example.test"


@pytest.mark.asyncio
async def test_refresh_rotation_replay_revokes_the_entire_family(
    auth_session: AsyncSession,
) -> None:
    service = AuthenticationService()
    registered = await service.register(
        auth_session,
        email=_unique_email(),
        display_name="Integration User",
        password="correct horse battery staple",
    )
    assert registered.user.role == "user"

    rotated = await service.refresh(auth_session, registered.refresh_token)
    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(auth_session, registered.refresh_token)
    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(auth_session, rotated.refresh_token)

    family = await auth_session.scalars(
        select(RefreshSession).where(RefreshSession.user_id == registered.user.id)
    )
    assert all(session.revoked_at is not None for session in family)


@pytest.mark.asyncio
async def test_expired_refresh_family_is_revoked(
    auth_session: AsyncSession,
) -> None:
    service = AuthenticationService()
    registered = await service.register(
        auth_session,
        email=_unique_email(),
        display_name="Expiry User",
        password="correct horse battery staple",
    )
    rotated = await service.refresh(auth_session, registered.refresh_token)
    current = await auth_session.scalar(
        select(RefreshSession)
        .where(
            RefreshSession.user_id == registered.user.id,
            RefreshSession.token_hash
            == hashlib.sha256(rotated.refresh_token.encode("utf-8")).hexdigest(),
        )
    )
    assert current is not None
    current.family_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await auth_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(auth_session, rotated.refresh_token)

    family = await auth_session.scalars(
        select(RefreshSession).where(RefreshSession.family_id == current.family_id)
    )
    assert all(session.revoked_at is not None for session in family)


@pytest.mark.asyncio
async def test_login_uses_generic_invalid_credentials(
    auth_session: AsyncSession,
) -> None:
    with pytest.raises(InvalidCredentialsError):
        await AuthenticationService().login(
            auth_session,
            email=_unique_email(),
            password="not-the-password",
        )


@pytest.mark.asyncio
async def test_logout_revokes_refresh_session(auth_session: AsyncSession) -> None:
    service = AuthenticationService()
    registered = await service.register(
        auth_session,
        email=_unique_email(),
        display_name="Logout User",
        password="correct horse battery staple",
    )

    await service.logout(auth_session, registered.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(auth_session, registered.refresh_token)


@pytest.mark.asyncio
async def test_duplicate_email_is_rejected_case_insensitively(
    auth_session: AsyncSession,
) -> None:
    service = AuthenticationService()
    email = _unique_email()
    await service.register(
        auth_session,
        email=email,
        display_name="First User",
        password="correct horse battery staple",
    )
    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(
            auth_session,
            email=email.upper(),
            display_name="Second User",
            password="correct horse battery staple",
        )
