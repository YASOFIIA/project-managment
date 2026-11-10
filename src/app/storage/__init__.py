from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> StorageBackend:
    """Return the configured storage backend singleton."""
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorage(base_dir=settings.local_storage_dir)
    elif settings.storage_backend == "s3":
        # S3 storage will be wired in Phase 9
        raise NotImplementedError("S3 storage backend will be enabled in Phase 9.")
    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")


__all__ = ["LocalStorage", "StorageBackend", "get_storage"]
