"""Tests for credential hashing and access-token validation."""

from uuid import uuid4

import jwt
import pytest
from backend.common.config import settings
from backend.services.passwords import hash_password, password_needs_rehash, verify_password
from backend.services.tokens import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def test_passwords_use_verifiable_one_way_hashes() -> None:
    password = "long-enough test password"
    password_hash = hash_password(password)

    assert password_hash.startswith("$argon2id$")
    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong password", password_hash)
    assert not verify_password(password, "not-a-password-hash")
    assert not password_needs_rehash(password_hash)


def test_access_token_validates_signature_and_standard_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    user_id = uuid4()
    monkeypatch.setattr(settings, "auth_private_key", private_pem.decode())
    monkeypatch.setattr(settings, "auth_public_keys", {"test-key": public_pem.decode()})
    monkeypatch.setattr(settings, "auth_signing_key_id", "test-key")

    token, expires_in = create_access_token(user_id)

    assert expires_in == settings.auth_access_token_ttl_seconds
    assert decode_access_token(token) == user_id
    assert jwt.get_unverified_header(token)["alg"] == "RS256"
    assert jwt.get_unverified_header(token)["kid"] == "test-key"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        jwt.encode({"sub": "not-a-uuid"}, "x" * 32, algorithm="HS256"),
    ],
)
def test_access_token_rejects_malformed_and_untrusted_tokens(
    token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "auth_public_keys", {})

    with pytest.raises(InvalidAccessTokenError, match="Invalid access token"):
        decode_access_token(token)
