from __future__ import annotations

import abc
from typing import Any, BinaryIO


def format_s3_key(
    project_id: int,
    document_id: int,
    stored_name: str = "",
    **kwargs: Any,
) -> str:
    """Generate canonical S3/storage object key layout.

    Format: projects/<project_id>/<document_id>/<stored_name>
    """
    name = stored_name or str(kwargs.get("filename", ""))
    return f"projects/{project_id}/{document_id}/{name}"


class StorageBackend(abc.ABC):
    """Abstract interface for document file storage (Local disk, AWS S3, etc.)."""

    @abc.abstractmethod
    def save(self, filename: str, content: BinaryIO | bytes) -> str:
        """Save a file into storage and return its unique stored filename/key.

        Args:
            filename: Target filename or key under which the content should be stored.
            content: File content as raw bytes or a readable binary file-like object.

        Returns:
            The stored filename/key that can be used to retrieve or delete the file.
        """
        ...

    @abc.abstractmethod
    def get(self, stored_filename: str) -> BinaryIO:
        """Retrieve a stored file as a readable binary stream.

        Args:
            stored_filename: The unique key/filename of the stored file.

        Returns:
            A readable binary file-like object (BinaryIO).

        Raises:
            FileNotFoundError: If the stored file does not exist in the backend.
        """
        ...

    @abc.abstractmethod
    def delete(self, stored_filename: str) -> bool:
        """Delete a stored file from the backend.

        Args:
            stored_filename: The unique key/filename of the stored file.

        Returns:
            True if the file existed and was deleted, False if it was not found.
        """
        ...

    @abc.abstractmethod
    def exists(self, stored_filename: str) -> bool:
        """Check whether a stored file exists in the backend.

        Args:
            stored_filename: The unique key/filename to check.

        Returns:
            True if the file exists, False otherwise.
        """
        ...
