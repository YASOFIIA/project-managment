from __future__ import annotations

import abc
from typing import Any, BinaryIO


# Generate S3 storage key: projects/<project_id>/<document_id>/<name>
def format_s3_key(
    project_id: int,
    document_id: int,
    stored_name: str = "",
    **kwargs: Any,
) -> str:
    name = stored_name or str(kwargs.get("filename", ""))
    return f"projects/{project_id}/{document_id}/{name}"


# Storage backend interface
class StorageBackend(abc.ABC):
    # Save file into storage and return key
    @abc.abstractmethod
    def save(self, filename: str, content: BinaryIO | bytes) -> str: ...

    # Read file from storage as binary stream
    @abc.abstractmethod
    def get(self, stored_filename: str) -> BinaryIO: ...

    # Delete file from storage
    @abc.abstractmethod
    def delete(self, stored_filename: str) -> bool: ...

    # Check if file exists in storage
    @abc.abstractmethod
    def exists(self, stored_filename: str) -> bool: ...
