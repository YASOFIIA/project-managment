from __future__ import annotations

from typing import Protocol, Self

from app.application.ports.document_repository import DocumentRepository
from app.application.ports.invitation_repository import InvitationRepository
from app.application.ports.project_repository import ProjectRepository
from app.application.ports.user_repository import UserRepository


# Unit of Work interface coordinating transactions
class UnitOfWork(Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def projects(self) -> ProjectRepository: ...

    @property
    def documents(self) -> DocumentRepository: ...

    @property
    def invitations(self) -> InvitationRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None: ...

    # Commit transaction
    def commit(self) -> None: ...

    # Rollback transaction
    def rollback(self) -> None: ...
