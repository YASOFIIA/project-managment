from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

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
        self._session.flush()
