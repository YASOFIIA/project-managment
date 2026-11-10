from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings

settings = get_settings()

# Initialize password hasher with Argon2id
_password_hash = PasswordHash((Argon2Hasher(),))


class SecurityError(Exception):
    """Base exception for security and authentication errors."""

    pass


class TokenExpiredError(SecurityError):
    """Raised when an authentication token is expired."""

    pass


class InvalidTokenError(SecurityError):
    """Raised when an authentication token is malformed, invalid, or tampered."""

    pass


def hash_password(plain_password: str) -> str:
    """Hash a raw password using the Argon2id algorithm.

    Never log or store plain passwords.
    """
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an Argon2id hash."""
    return _password_hash.verify(plain_password, hashed_password)


def create_access_token(
    user_id: int,
    login: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a signed JWT access token with user claims and exactly 1-hour expiry."""
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "login": login,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed JWT access token.

    Validates signature and expiration timestamp.
    Raises:
        TokenExpiredError: if the token lifetime has elapsed.
        InvalidTokenError: if signature is invalid or payload is corrupted.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid token signature or payload") from exc
