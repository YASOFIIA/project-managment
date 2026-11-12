from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UploadedFile(Protocol):
    """Port representing an uploaded file independent of web frameworks."""

    filename: str | None
    content_type: str | None

    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes from the uploaded file."""
        ...
