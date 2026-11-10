from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth import authenticate_user, register_user

router = APIRouter(tags=["Authentication"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/auth",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Register a new user account with login and confirmed password.",
)
def register(
    data: UserRegisterRequest,
    db: DbSession,
) -> UserResponse:
    """Create user endpoint."""
    user = register_user(db=db, data=data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login into service",
    description="Authenticate user with login and password, returning 1-hour JWT token.",
)
def login(
    data: UserLoginRequest,
    db: DbSession,
) -> TokenResponse:
    """Login into service endpoint."""
    token = authenticate_user(db=db, data=data)
    return TokenResponse(access_token=token, token_type="bearer")
