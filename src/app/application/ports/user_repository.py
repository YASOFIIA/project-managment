from __future__ import annotations

from typing import Protocol

from app.models.user import User


class UserRepository(Protocol):
    """Port for user persistence operations."""

    def get_by_id(self, user_id: int) -> User | None:
        """Find user by primary key."""
        ...

    def get_by_login(self, login: str) -> User | None:
        """Find user by unique login."""
        ...

    def add(self, user: User) -> None:
        """Add and flush user entity."""
        ...
