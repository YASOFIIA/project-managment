from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import LoginTaken
from app.models.user import User


# SQLAlchemy adapter for user persistence
class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # Find user by primary key
    def get_by_id(self, user_id: int) -> User | None:
        return self._session.get(User, user_id)

    # Find user by login
    def get_by_login(self, login: str) -> User | None:
        stmt = select(User).where(User.login == login)
        return self._session.scalar(stmt)

    # Add and flush user
    def add(self, user: User) -> None:
        self._session.add(user)
        try:
            self._session.flush()
        except IntegrityError as err:
            orig = getattr(err, "orig", None)
            sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
            if sqlstate == "23505" or "unique" in str(err).lower():
                raise LoginTaken(f"Login {user.login!r} is already taken") from err
            raise
