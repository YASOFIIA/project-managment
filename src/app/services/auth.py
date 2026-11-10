from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest


def register_user(db: Session, data: UserRegisterRequest) -> User:
    """Register a new user with unique login and Argon2-hashed password.

    Raises:
        HTTPException(409): if the login is already taken.
    """
    existing_user = db.scalar(select(User).where(User.login == data.login))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Login {data.login!r} is already taken",
        )

    hashed_pw = hash_password(data.password)
    new_user = User(
        login=data.login,
        hashed_password=hashed_pw,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, data: UserLoginRequest) -> str:
    """Authenticate user credentials and issue a signed 1-hour JWT access token.

    Raises:
        HTTPException(401): if the username or password is invalid.
    """
    user = db.scalar(select(User).where(User.login == data.login))
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
        )

    return create_access_token(user_id=user.id, login=user.login)
