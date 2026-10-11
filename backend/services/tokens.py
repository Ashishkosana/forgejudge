"""JWT access token signing and validation."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from backend.common.config import settings
from jwt import InvalidTokenError

ALGORITHM = "RS256"


class InvalidAccessTokenError(ValueError):
    """Raised when an access token is invalid or cannot be verified."""


def create_access_token(user_id: UUID) -> tuple[str, int]:
    private_key = settings.auth_private_key.replace("\\n", "\n")
    if not private_key:
        raise RuntimeError("Authentication signing key is not configured")
    expires_in = settings.auth_access_token_ttl_seconds
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": str(uuid4()),
        "typ": "access",
    }
    token = jwt.encode(
        payload,
        private_key,
        algorithm=ALGORITHM,
        headers={"kid": settings.auth_signing_key_id},
    )
    return token, expires_in


def decode_access_token(token: str) -> UUID:
    try:
        header = jwt.get_unverified_header(token)
        key_id = header.get("kid")
        if header.get("alg") != ALGORITHM or not isinstance(key_id, str):
            raise InvalidAccessTokenError("Invalid access token")
        public_key = settings.auth_public_keys.get(key_id)
        if not public_key:
            raise InvalidAccessTokenError("Invalid access token")
        payload = jwt.decode(
            token,
            public_key.replace("\\n", "\n"),
            algorithms=[ALGORITHM],
            issuer=settings.auth_issuer,
            audience=settings.auth_audience,
            options={"require": ["sub", "iss", "aud", "iat", "exp", "jti", "typ"]},
        )
        if payload["typ"] != "access":
            raise InvalidAccessTokenError("Invalid access token")
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessTokenError("Invalid access token") from exc
