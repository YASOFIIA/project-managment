from __future__ import annotations

from typing import Protocol

from app.models.document import Document


class DocumentRepository(Protocol):
    """Port for document persistence operations."""

    def get_by_id(self, document_id: int) -> Document | None:
        """Find document by primary key."""
        ...

    def list_by_project_id(self, project_id: int) -> list[Document]:
        """Find all documents belonging to a project."""
        ...

    def list_stored_filenames(self, project_id: int) -> list[str]:
        """Retrieve storage keys (stored_filename) for all documents in a project."""
        ...

    def add(self, document: Document) -> None:
        """Add and flush document entity."""
        ...

    def delete(self, document: Document) -> None:
        """Delete document entity."""
        ...
