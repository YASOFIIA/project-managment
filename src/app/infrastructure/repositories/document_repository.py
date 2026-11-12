from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class SqlAlchemyDocumentRepository:
    """SQLAlchemy adapter for document persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, document_id: int) -> Document | None:
        """Find document by primary key."""
        return self._session.get(Document, document_id)

    def list_by_project_id(self, project_id: int) -> list[Document]:
        """Find all documents belonging to a project."""
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_stored_filenames(self, project_id: int) -> list[str]:
        """Retrieve storage keys (stored_filename) for all documents in a project."""
        stmt = (
            select(Document.stored_filename)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def add(self, document: Document) -> None:
        """Add and flush document entity."""
        self._session.add(document)
        self._session.flush()

    def delete(self, document: Document) -> None:
        """Delete document entity."""
        self._session.delete(document)
