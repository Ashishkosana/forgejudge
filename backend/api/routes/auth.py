"""Authentication endpoints intended for the trusted Next.js BFF."""

from __future__ import annotations

import hmac
import ipaddress
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user, get_redis
from backend.api.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegistrationRequest,
    UserRead,
)
from backend.common.config import settings
from backend.common.database import get_session
from backend.models.user import User
from backend.services.authentication import (
    AuthenticationService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from backend.services.rate_limit import RateLimitUnavailableError, consume_auth_attempt

router = APIRouter(prefix="/auth", tags=["authentication"])
authentication_service = AuthenticationService()


async def require_bff_secret(
    provided_secret: Annotated[str | None, Header(alias="X-ForgeJudge-BFF-Secret")] = None,
) -> None:
    configured_secret = settings.bff_shared_secret
    if (
        len(configured_secret) < 32
        or not settings.auth_private_key
        or settings.auth_signing_key_id not in settings.auth_public_keys
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured",
        )
    if provided_secret is None or not hmac.compare_digest(provided_secret, configured_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def _remote_host(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        candidate = forwarded_for.split(",", maxsplit=1)[0].strip()
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    return request.client.host if request.client is not None else "unknown"


async def _enforce_rate_limit(redis: Redis, request: Request, identity: str) -> None:
    try:
        allowed = await consume_auth_attempt(redis, _remote_host(request), identity=identity)
    except RateLimitUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable",
        ) from exc
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts",
            headers={"Retry-After": "60"},
        )


def _token_response(auth_session) -> AuthTokenResponse:
    return AuthTokenResponse(
        access_token=auth_session.access_token,
        refresh_token=auth_session.refresh_token,
        expires_in=auth_session.expires_in,
        user=UserRead.model_validate(auth_session.user),
    )


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_bff_secret)],
)
async def register(
    payload: RegistrationRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> AuthTokenResponse:
    await _enforce_rate_limit(redis, request, payload.email)
    try:
        auth_session = await authentication_service.register(
            session,
            email=payload.email,
            display_name=payload.display_name,
            password=payload.password,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc
    response.headers["Cache-Control"] = "no-store"
    return _token_response(auth_session)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    dependencies=[Depends(require_bff_secret)],
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> AuthTokenResponse:
    await _enforce_rate_limit(redis, request, payload.email)
    try:
        auth_session = await authentication_service.login(
            session, email=payload.email, password=payload.password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    response.headers["Cache-Control"] = "no-store"
    return _token_response(auth_session)


@router.post(
    "/refresh",
    response_model=AuthTokenResponse,
    dependencies=[Depends(require_bff_secret)],
)
async def refresh(
    payload: RefreshRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthTokenResponse:
    try:
        auth_session = await authentication_service.refresh(session, payload.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh session",
        ) from exc
    response.headers["Cache-Control"] = "no-store"
    return _token_response(auth_session)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_bff_secret)],
)
async def logout(
    payload: LogoutRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await authentication_service.logout(session, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_bff_secret)],
)
async def logout_all(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await authentication_service.logout_all(session, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
async def current_user(
    user: Annotated[User, Depends(get_current_user)], response: Response
) -> UserRead:
    response.headers["Cache-Control"] = "no-store"
    return UserRead.model_validate(user)
