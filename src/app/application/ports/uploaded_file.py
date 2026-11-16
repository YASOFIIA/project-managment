from __future__ import annotations

from typing import Protocol, runtime_checkable


# Uploaded file interface
@runtime_checkable
class UploadedFile(Protocol):
    filename: str | None
    content_type: str | None

    # Read bytes from uploaded file
    def read(self, size: int = -1) -> bytes: ...
