from functools import lru_cache

from app.application.ports.storage import StorageBackend
from app.core.config import get_settings
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage


@lru_cache
def get_storage() -> StorageBackend:
    """Return the configured storage backend singleton."""
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorage(base_dir=settings.local_storage_dir)
    elif settings.storage_backend == "s3":
        return S3Storage(
            bucket_name=settings.s3_bucket_name,
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")


__all__ = ["LocalStorage", "S3Storage", "StorageBackend", "get_storage"]
