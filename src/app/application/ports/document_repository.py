from __future__ import annotations

from typing import Protocol

from app.models.document import Document


# Document repository port
class DocumentRepository(Protocol):
    # Find document by ID
    def get_by_id(self, document_id: int) -> Document | None: ...

    # Find all documents in project
    def list_by_project_id(self, project_id: int) -> list[Document]: ...

    # Get stored filenames for a project
    def list_stored_filenames(self, project_id: int) -> list[str]: ...

    # Add and flush document
    def add(self, document: Document) -> None: ...

    # Delete document
    def delete(self, document: Document) -> None: ...
