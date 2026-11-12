from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import LoginTaken
from app.models.user import User


class SqlAlchemyUserRepository:
    """SQLAlchemy adapter for user persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> User | None:
        """Find user by primary key."""
        return self._session.get(User, user_id)

    def get_by_login(self, login: str) -> User | None:
        """Find user by unique login."""
        stmt = select(User).where(User.login == login)
        return self._session.scalar(stmt)

    def add(self, user: User) -> None:
        """Add and flush user entity."""
        self._session.add(user)
        try:
            self._session.flush()
        except IntegrityError as err:
            orig = getattr(err, "orig", None)
            sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
            if sqlstate == "23505" or "unique" in str(err).lower():
                raise LoginTaken(f"Login {user.login!r} is already taken") from err
            raise
