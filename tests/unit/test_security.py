from datetime import timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# Check Argon2 hashing is secure and verifies passwords correctly
def test_password_hashing_and_verification() -> None:
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    # Password hash must not be plain text and must follow Argon2 format
    assert hashed != password
    assert hashed.startswith("$argon2")

    # Correct password succeeds
    assert verify_password(password, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False


# Check create_access_token issues a token with valid claims and 1-hour expiry
def test_jwt_token_creation_and_claims() -> None:
    user_id = 42
    login = "test_user"

    token = create_access_token(user_id=user_id, login=login)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["login"] == "test_user"
    assert "iat" in payload
    assert "exp" in payload

    # Expiry must be exactly 1 hour (3600 seconds) after issuance
    lifetime = payload["exp"] - payload["iat"]
    assert lifetime == 3600


# Check an expired token raises TokenExpiredError
def test_jwt_token_expired_raises_error() -> None:
    token = create_access_token(
        user_id=1,
        login="expired_user",
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(TokenExpiredError, match="Token has expired"):
        decode_access_token(token)


# Check modifying the token payload raises InvalidTokenError
def test_jwt_token_tampered_raises_error() -> None:
    token = create_access_token(user_id=1, login="legit_user")
    parts = token.split(".")

    # Tamper with the payload part
    tampered_token = f"{parts[0]}.eyJob21lIjoidmFsaWQifQ.{parts[2]}"

    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered_token)


# Check a token signed with an unknown secret key is rejected
def test_jwt_token_signed_with_wrong_key_raises_error() -> None:
    settings = get_settings()
    other_key = "different-unknown-secret-key-at-least-32-chars-long"

    fake_token = jwt.encode(
        {"sub": "1", "login": "attacker"},
        other_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(fake_token)
