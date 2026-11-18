from __future__ import annotations

import abc
from typing import Any, BinaryIO

THUMBNAIL_PREFIX: str = "thumb_"


# Generate S3 storage key: projects/<project_id>/<document_id>/<name>
def format_s3_key(
    project_id: int,
    document_id: int,
    stored_name: str = "",
    **kwargs: Any,
) -> str:
    name = stored_name or str(kwargs.get("filename", ""))
    return f"projects/{project_id}/{document_id}/{name}"


# Build S3 thumbnail key in the same directory as the original object: <dir>/thumb_<filename>
def build_thumbnail_key(original_key: str) -> str:
    parts = original_key.rsplit("/", 1)
    if len(parts) == 2:
        return f"{parts[0]}/{THUMBNAIL_PREFIX}{parts[1]}"
    return f"{THUMBNAIL_PREFIX}{original_key}"


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
