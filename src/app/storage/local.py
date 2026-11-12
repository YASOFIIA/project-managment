from pathlib import Path
from typing import BinaryIO

from app.application.ports.storage import StorageBackend


class LocalStorage(StorageBackend):
    """Local filesystem implementation of StorageBackend with path-traversal safeguards."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, stored_filename: str) -> Path:
        """Resolve a filename against base_dir while strictly preventing path traversal.

        Raises:
            ValueError: If the target path attempts to escape base_dir.
        """
        clean_name = stored_filename.strip().lstrip("/\\")
        target_path = (self.base_dir / clean_name).resolve()

        if not target_path.is_relative_to(self.base_dir):
            raise ValueError(f"Path traversal detected for filename: '{stored_filename}'")

        return target_path

    def save(self, filename: str, content: BinaryIO | bytes) -> str:
        """Save file content to local filesystem."""
        target_path = self._resolve_safe_path(filename)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, bytes):
            target_path.write_bytes(content)
        else:
            if hasattr(content, "seek"):
                content.seek(0)
            with open(target_path, "wb") as f:
                while chunk := content.read(8192):
                    f.write(chunk)

        return filename

    def get(self, stored_filename: str) -> BinaryIO:
        """Open and return a readable binary stream for the stored file."""
        target_path = self._resolve_safe_path(stored_filename)
        if not target_path.is_file():
            raise FileNotFoundError(f"Stored file '{stored_filename}' not found.")
        return open(target_path, "rb")  # noqa: SIM115

    def delete(self, stored_filename: str) -> bool:
        """Delete a file from the local storage directory."""
        target_path = self._resolve_safe_path(stored_filename)
        if target_path.is_file():
            target_path.unlink()
            return True
        return False

    def exists(self, stored_filename: str) -> bool:
        """Check if file exists on local disk."""
        target_path = self._resolve_safe_path(stored_filename)
        return target_path.is_file()
