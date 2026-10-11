"""Registration, login, and refresh-session lifecycle."""

from __future__ import annotations

import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.common.config import settings
from backend.models.refresh_session import RefreshSession
from backend.models.user import User
from backend.services.passwords import hash_password, password_needs_rehash, verify_password
from backend.services.tokens import create_access_token
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


@dataclass(frozen=True, slots=True)
class AuthSession:
    user: User
    access_token: str
    refresh_token: str
    expires_in: int


class InvalidCredentialsError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_refresh_session(
    user: User, *, family_id: UUID | None = None, family_expires_at: datetime | None = None
) -> tuple[RefreshSession, str]:
    now = datetime.now(UTC)
    absolute_expiry = family_expires_at or now + timedelta(
        days=settings.auth_refresh_absolute_days
    )
    idle_expiry = now + timedelta(days=settings.auth_refresh_idle_days)
    token = secrets.token_urlsafe(48)
    return (
        RefreshSession(
            user_id=user.id,
            token_hash=_token_hash(token),
            family_id=family_id or uuid4(),
            expires_at=min(idle_expiry, absolute_expiry),
            family_expires_at=absolute_expiry,
        ),
        token,
    )


def _session_response(user: User, refresh_token: str) -> AuthSession:
    access_token, expires_in = create_access_token(user.id)
    return AuthSession(user, access_token, refresh_token, expires_in)


async def _revoke_family(session: AsyncSession, family_id: UUID, now: datetime) -> None:
    await session.execute(
        update(RefreshSession)
        .where(
            RefreshSession.family_id == family_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=now, updated_at=now)
    )


class AuthenticationService:
    async def register(
        self,
        session: AsyncSession,
        *,
        email: str,
        display_name: str,
        password: str,
    ) -> AuthSession:
        normalized_email = normalize_email(email)
        user = User(
            email=normalized_email,
            display_name=display_name.strip(),
            password_hash=await asyncio.to_thread(hash_password, password),
            role="user",
            is_active=True,
        )
        session.add(user)
        try:
            await session.flush()
            refresh_session, refresh_token = _new_refresh_session(user)
            session.add(refresh_session)
            result = _session_response(user, refresh_token)
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            constraint_name = getattr(exc.orig, "constraint_name", None)
            if constraint_name is None:
                constraint_name = getattr(
                    getattr(exc.orig, "diag", None), "constraint_name", None
                )
            if constraint_name not in {"uq_users_email_normalized", "users_email_key"}:
                raise
            raise EmailAlreadyRegisteredError from exc
        return result

    async def login(
        self, session: AsyncSession, *, email: str, password: str
    ) -> AuthSession:
        user = await session.scalar(
            select(User).where(func.lower(func.trim(User.email)) == normalize_email(email))
        )
        stored_hash = user.password_hash if user and user.password_hash else _DUMMY_PASSWORD_HASH
        valid_password = await asyncio.to_thread(verify_password, password, stored_hash)
        if user is None or not user.is_active or not user.password_hash or not valid_password:
            raise InvalidCredentialsError
        if password_needs_rehash(user.password_hash):
            user.password_hash = await asyncio.to_thread(hash_password, password)
        now = datetime.now(UTC)
        user.last_login_at = now
        refresh_session, refresh_token = _new_refresh_session(user)
        session.add(refresh_session)
        result = _session_response(user, refresh_token)
        await session.commit()
        return result

    async def refresh(self, session: AsyncSession, refresh_token: str) -> AuthSession:
        token_hash = _token_hash(refresh_token)
        stored = await session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_hash)
            .with_for_update()
        )
        if stored is None:
            raise InvalidRefreshTokenError

        now = datetime.now(UTC)
        if stored.revoked_at is not None:
            await _revoke_family(session, stored.family_id, now)
            await session.commit()
            raise InvalidRefreshTokenError
        if stored.expires_at <= now or stored.family_expires_at <= now:
            await _revoke_family(session, stored.family_id, now)
            await session.commit()
            raise InvalidRefreshTokenError

        user = await session.get(User, stored.user_id)
        if user is None or not user.is_active:
            await _revoke_family(session, stored.family_id, now)
            await session.commit()
            raise InvalidRefreshTokenError

        replacement, next_token = _new_refresh_session(
            user,
            family_id=stored.family_id,
            family_expires_at=stored.family_expires_at,
        )
        stored.revoked_at = now
        stored.last_used_at = now
        session.add(replacement)
        await session.flush()
        stored.replaced_by_id = replacement.id
        result = _session_response(user, next_token)
        await session.commit()
        return result

    async def logout(self, session: AsyncSession, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        stored = await session.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == _token_hash(refresh_token))
            .with_for_update()
        )
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)
            await session.commit()

    async def logout_all(self, session: AsyncSession, user_id: UUID) -> None:
        now = datetime.now(UTC)
        await session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now, updated_at=now)
        )
        await session.commit()
