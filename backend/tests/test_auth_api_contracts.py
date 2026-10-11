"""Fast unit tests for authentication contracts and fail-closed dependencies."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from backend.api.routes.auth import require_bff_secret
from backend.api.schemas.auth import RegistrationRequest, UserRead
from backend.common.config import settings
from backend.services.rate_limit import (
    RateLimitUnavailableError,
    consume_auth_attempt,
)
from fastapi import HTTPException
from pydantic import ValidationError


def test_registration_normalizes_input_and_rejects_blank_display_name() -> None:
    request = RegistrationRequest(
        email="  person@example.test ",
        display_name="  Example Person ",
        password="correct horse battery staple",
    )

    assert request.email == "person@example.test"
    assert request.display_name == "Example Person"
    with pytest.raises(ValidationError):
        RegistrationRequest(
            email="person@example.test",
            display_name="  ",
            password="correct horse battery staple",
        )


def test_user_response_reads_orm_attributes_without_exposing_credentials() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="person@example.test",
        display_name="Example",
        role="user",
        password_hash="must-not-be-serialized",
    )

    response = UserRead.model_validate(user)

    assert response.email == user.email
    assert "password_hash" not in response.model_dump()


@pytest.mark.asyncio
async def test_bff_secret_is_unavailable_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "bff_shared_secret", "")

    with pytest.raises(HTTPException) as error:
        await require_bff_secret(None)

    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_bff_secret_requires_constant_time_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "s" * 40
    monkeypatch.setattr(settings, "bff_shared_secret", secret)
    monkeypatch.setattr(settings, "auth_private_key", "configured")
    monkeypatch.setattr(settings, "auth_public_keys", {"local": "configured"})
    monkeypatch.setattr(settings, "auth_signing_key_id", "local")

    await require_bff_secret(secret)
    with pytest.raises(HTTPException) as error:
        await require_bff_secret("wrong")
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_auth_rate_limit_hashes_source_and_enforces_threshold() -> None:
    class FakeRedis:
        calls: list[tuple[object, ...]] = []

        async def eval(self, *args: object) -> list[int]:
            self.calls.append(args)
            return [2, 2]

    redis = FakeRedis()

    assert (
        await consume_auth_attempt(
            redis,
            "203.0.113.5",
            identity="PERSON@example.test",
            source_limit=1,
        )
        is False
    )
    source_key = str(redis.calls[0][2])
    identity_key = str(redis.calls[0][3])
    assert source_key.startswith("forgejudge:auth-rate:source:")
    assert identity_key.startswith("forgejudge:auth-rate:identity:")
    assert "203.0.113.5" not in source_key
    assert "PERSON@example.test" not in identity_key
    assert redis.calls[0][4:] == (60, 60)


@pytest.mark.asyncio
async def test_auth_rate_limit_fails_closed_when_redis_is_unavailable() -> None:
    class UnavailableRedis:
        async def eval(self, *args: object) -> list[int]:
            raise TimeoutError

    with pytest.raises(RateLimitUnavailableError):
        await consume_auth_attempt(
            UnavailableRedis(),
            "203.0.113.5",
            identity="person@example.test",
        )
