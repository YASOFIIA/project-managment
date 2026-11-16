from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


# SQLAlchemy adapter for document persistence
class SqlAlchemyDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # Find document by ID
    def get_by_id(self, document_id: int) -> Document | None:
        return self._session.get(Document, document_id)

    # Find all documents in project
    def list_by_project_id(self, project_id: int) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    # Get stored filenames for a project
    def list_stored_filenames(self, project_id: int) -> list[str]:
        stmt = (
            select(Document.stored_filename)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    # Add and flush document
    def add(self, document: Document) -> None:
        self._session.add(document)
        self._session.flush()

    # Delete document
    def delete(self, document: Document) -> None:
        self._session.delete(document)
