from __future__ import annotations

from typing import Protocol

from app.models.user import User


# User repository port
class UserRepository(Protocol):
    # Find user by primary key
    def get_by_id(self, user_id: int) -> User | None: ...

    # Find user by login
    def get_by_login(self, login: str) -> User | None: ...

    # Add and flush user
    def add(self, user: User) -> None: ...
