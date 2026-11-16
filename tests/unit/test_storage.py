import io
from pathlib import Path

import pytest

from app.core.config import Settings
from app.storage import LocalStorage, get_storage


# Check saving and reading binary data using bytes
def test_local_storage_save_and_get_bytes(tmp_path: Path) -> None:
    storage = LocalStorage(base_dir=tmp_path)
    content = b"Hello, secure local storage!"
    filename = "documents/test_file.txt"

    stored_name = storage.save(filename, content)
    assert stored_name == filename
    assert storage.exists(filename) is True

    stream = storage.get(filename)
    try:
        read_content = stream.read()
        assert read_content == content
    finally:
        stream.close()


# Check saving and reading binary data using a binary stream
def test_local_storage_save_and_get_stream(tmp_path: Path) -> None:
    storage = LocalStorage(base_dir=tmp_path)
    content = b"Streamed report contents for project"
    stream_in = io.BytesIO(content)
    filename = "reports/project_1/report.pdf"

    storage.save(filename, stream_in)
    assert storage.exists(filename) is True

    stream_out = storage.get(filename)
    try:
        assert stream_out.read() == content
    finally:
        stream_out.close()


# Check file deletion and return codes
def test_local_storage_delete(tmp_path: Path) -> None:
    storage = LocalStorage(base_dir=tmp_path)
    filename = "temp_doc.bin"

    # Non-existent deletion returns False
    assert storage.delete(filename) is False

    # Save and then delete
    storage.save(filename, b"will be deleted")
    assert storage.exists(filename) is True

    assert storage.delete(filename) is True
    assert storage.exists(filename) is False
    assert storage.delete(filename) is False


# Check attempting to get a non-existent file raises FileNotFoundError
def test_local_storage_get_nonexistent_raises_file_not_found(tmp_path: Path) -> None:
    storage = LocalStorage(base_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="Stored file 'missing.txt' not found"):
        storage.get("missing.txt")


# Check path traversal attempts raise ValueError
def test_local_storage_path_traversal_prevention(tmp_path: Path) -> None:
    storage = LocalStorage(base_dir=tmp_path)

    traversal_filenames = [
        "../../etc/passwd",
        "sub/../../../root/secret.key",
        "../escaped.txt",
    ]

    for fname in traversal_filenames:
        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.save(fname, b"malicious data")

        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.get(fname)

        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.delete(fname)

        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.exists(fname)


# Check the get_storage factory returns LocalStorage and handles configs
def test_get_storage_factory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Test local backend
    custom_settings = Settings(
        jwt_secret_key="test-secret-32-chars-long-minimum!",
        lambda_callback_secret="test-lambda-secret",
        storage_backend="local",
        local_storage_dir=str(tmp_path),
    )
    monkeypatch.setattr("app.storage.get_settings", lambda: custom_settings)
    get_storage.cache_clear()

    storage = get_storage()
    assert isinstance(storage, LocalStorage)

    # Test s3 backend returns S3Storage (Phase 9)
    s3_settings = Settings(
        jwt_secret_key="test-secret-32-chars-long-minimum!",
        lambda_callback_secret="test-lambda-secret",
        storage_backend="s3",
    )
    monkeypatch.setattr("app.storage.get_settings", lambda: s3_settings)
    get_storage.cache_clear()

    from app.storage.s3 import S3Storage

    s3_storage = get_storage()
    assert isinstance(s3_storage, S3Storage)

    # Clean up lru_cache
    get_storage.cache_clear()
