from __future__ import annotations

from typing import Protocol, Self

from app.application.ports.document_repository import DocumentRepository
from app.application.ports.project_repository import ProjectRepository
from app.application.ports.user_repository import UserRepository


class UnitOfWork(Protocol):
    """Unit of Work interface coordinating repository operations and transaction boundary."""

    @property
    def users(self) -> UserRepository:
        ...

    @property
    def projects(self) -> ProjectRepository:
        ...

    @property
    def documents(self) -> DocumentRepository:
        ...

    def __enter__(self) -> Self:
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        ...

    def commit(self) -> None:
        """Commit current transaction boundary."""
        ...

    def rollback(self) -> None:
        """Rollback current transaction boundary."""
        ...
