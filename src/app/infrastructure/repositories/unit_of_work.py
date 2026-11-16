from __future__ import annotations

from typing import Self

from sqlalchemy.orm import Session

from app.application.ports.document_repository import DocumentRepository
from app.application.ports.invitation_repository import InvitationRepository
from app.application.ports.project_repository import ProjectRepository
from app.application.ports.user_repository import UserRepository
from app.infrastructure.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.repositories.invitation import (
    SqlAlchemyInvitationRepository,
)
from app.infrastructure.repositories.project_repository import (
    SqlAlchemyProjectRepository,
)
from app.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)


# SQLAlchemy UnitOfWork implementation
class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.users: UserRepository = SqlAlchemyUserRepository(session)
        self.projects: ProjectRepository = SqlAlchemyProjectRepository(session)
        self.documents: DocumentRepository = SqlAlchemyDocumentRepository(session)
        self.invitations: InvitationRepository = SqlAlchemyInvitationRepository(session)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    # Commit transaction
    def commit(self) -> None:
        self._session.commit()

    # Rollback transaction
    def rollback(self) -> None:
        self._session.rollback()
