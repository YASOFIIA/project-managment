from __future__ import annotations

from app.application.ports.unit_of_work import UnitOfWork
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.errors import EmailTaken, InvalidCredentials, LoginTaken
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest


# Register user with unique login, email, and hashed password
def register_user(uow: UnitOfWork, data: UserRegisterRequest) -> User:
    with uow:
        existing_user = uow.users.get_by_login(data.login)
        if existing_user is not None:
            raise LoginTaken(f"Login {data.login!r} is already taken")

        existing_email = uow.users.get_by_email(data.email)
        if existing_email is not None:
            raise EmailTaken(f"Email {data.email!r} is already taken")

        hashed_pw = hash_password(data.password)
        new_user = User(
            login=data.login,
            email=data.email,
            hashed_password=hashed_pw,
        )
        try:
            uow.users.add(new_user)
        except (LoginTaken, EmailTaken):
            uow.rollback()
            raise

        uow.commit()
        return new_user


# Authenticate user and issue 1-hour JWT token
def authenticate_user(uow: UnitOfWork, data: UserLoginRequest) -> str:
    user = uow.users.get_by_login(data.login)
    if user is None or not verify_password(data.password, user.hashed_password):
        raise InvalidCredentials("Invalid login or password")

    return create_access_token(user_id=user.id, login=user.login)
