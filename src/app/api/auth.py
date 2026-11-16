from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_uow
from app.application.ports.unit_of_work import UnitOfWork
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth import authenticate_user, register_user

router = APIRouter(tags=["Authentication"])

UowDep = Annotated[UnitOfWork, Depends(get_uow)]


# Register user endpoint
@router.post(
    "/auth",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Register a new user account with login and confirmed password.",
)
def register(
    data: UserRegisterRequest,
    uow: UowDep,
) -> UserResponse:
    user = register_user(uow=uow, data=data)
    return UserResponse.model_validate(user)


# Login endpoint
@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login into service",
    description="Authenticate user with login and password, returning 1-hour JWT token.",
)
def login(
    data: UserLoginRequest,
    uow: UowDep,
) -> TokenResponse:
    token = authenticate_user(uow=uow, data=data)
    return TokenResponse(access_token=token, token_type="bearer")


# Get current user profile endpoint
@router.get(
    "/auth/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Retrieve the profile of the currently authenticated user.",
)
def get_current_user_profile(
    current_user: CurrentUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)
