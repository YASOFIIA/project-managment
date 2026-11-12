import hmac
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.ports.unit_of_work import UnitOfWork
from app.core.config import Settings, get_settings
from app.core.security import InvalidTokenError, TokenExpiredError, decode_access_token
from app.db.session import get_db
from app.infrastructure.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.models.user import User

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT Bearer token issued by POST /login",
)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """FastAPI dependency to extract and validate the JWT Bearer token and return the User.

    Raises:
        HTTPException(401): if the token is missing, invalid, expired, or user not found.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id_str = payload.get("sub")
    if not user_id_str or not user_id_str.isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, int(user_id_str))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_lambda_secret(
    x_lambda_secret: Annotated[str | None, Header(alias="X-Lambda-Secret")] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> str:
    """FastAPI dependency to verify incoming internal webhook requests carry the secret header.

    Raises:
        HTTPException(403): If the secret header is missing or does not match.
    """
    if settings is None:
        settings = get_settings()

    if not x_lambda_secret or not hmac.compare_digest(
        x_lambda_secret.encode("utf-8"),
        settings.lambda_callback_secret.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: invalid or missing Lambda callback secret",
        )

    return x_lambda_secret


def get_uow(
    db: Annotated[Session, Depends(get_db)],
) -> Generator[UnitOfWork, None, None]:
    """Provide a UnitOfWork bound to the current database session."""
    yield SqlAlchemyUnitOfWork(db)
