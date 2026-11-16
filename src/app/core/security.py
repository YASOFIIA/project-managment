from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings

settings = get_settings()

# Initialize password hasher with Argon2id
_password_hash = PasswordHash((Argon2Hasher(),))


# Base exception for security errors
class SecurityError(Exception):
    pass


# Raised when auth token has expired
class TokenExpiredError(SecurityError):
    pass


# Raised when auth token is invalid or tampered with
class InvalidTokenError(SecurityError):
    pass


# Hash password with Argon2id
def hash_password(plain_password: str) -> str:
    return _password_hash.hash(plain_password)


# Verify password against Argon2id hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _password_hash.verify(plain_password, hashed_password)


# Create JWT token with 1h expiry
def create_access_token(
    user_id: int,
    login: str,
    expires_delta: timedelta | None = None,
) -> str:
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


# Decode and validate signed JWT token
def decode_access_token(token: str) -> dict[str, Any]:
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
