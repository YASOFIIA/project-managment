import io
from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.storage import get_storage
from app.storage.s3 import S3Storage, format_s3_key


def test_format_s3_key() -> None:
    """Verify S3 key structure adheres to projects/<project_id>/<document_id>/<stored_name>."""
    key = format_s3_key(project_id=12, document_id=45, stored_name="specs.pdf")
    assert key == "projects/12/45/specs.pdf"


def test_s3_storage_save_bytes_and_stream() -> None:
    """Verify saving bytes and stream via S3Storage."""
    mock_client = MagicMock()
    storage = S3Storage(bucket_name="test-bucket", s3_client=mock_client)

    # 1. Save bytes
    key1 = "projects/1/1/file1.pdf"
    content_bytes = b"%PDF-1.4 sample content"
    res1 = storage.save(key1, content_bytes)
    assert res1 == key1
    mock_client.put_object.assert_called_with(
        Bucket="test-bucket",
        Key=key1,
        Body=content_bytes,
    )

    # 2. Save stream
    key2 = "projects/1/2/file2.pdf"
    stream = io.BytesIO(b"%PDF-1.4 stream content")
    res2 = storage.save(key2, stream)
    assert res2 == key2
    mock_client.put_object.assert_called_with(
        Bucket="test-bucket",
        Key=key2,
        Body=b"%PDF-1.4 stream content",
    )


def test_s3_storage_get_success() -> None:
    """Verify retrieving an existing object returns its Body stream."""
    mock_client = MagicMock()
    fake_body = io.BytesIO(b"%PDF-1.4 downloaded data")
    mock_client.get_object.return_value = {"Body": fake_body}

    storage = S3Storage(bucket_name="test-bucket", s3_client=mock_client)
    stream = storage.get("projects/5/9/doc.pdf")

    assert stream.read() == b"%PDF-1.4 downloaded data"
    mock_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="projects/5/9/doc.pdf",
    )


def test_s3_storage_get_not_found_raises_file_not_found() -> None:
    """Verify NoSuchKey error raises standard FileNotFoundError."""
    mock_client = MagicMock()
    error_response: Any = {
        "Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }
    mock_client.get_object.side_effect = ClientError(error_response, "GetObject")

    storage = S3Storage(bucket_name="test-bucket", s3_client=mock_client)
    with pytest.raises(FileNotFoundError, match="S3 object 'missing.pdf' not found"):
        storage.get("missing.pdf")


def test_s3_storage_exists() -> None:
    """Verify exists returns True on success and False on 404/NotFound."""
    mock_client = MagicMock()
    storage = S3Storage(bucket_name="test-bucket", s3_client=mock_client)

    # Object exists
    mock_client.head_object.return_value = {"ContentLength": 100}
    assert storage.exists("exists.pdf") is True

    # Object does not exist
    error_response: Any = {
        "Error": {"Code": "404", "Message": "Not Found"},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }
    mock_client.head_object.side_effect = ClientError(error_response, "HeadObject")
    assert storage.exists("missing.pdf") is False


def test_s3_storage_delete() -> None:
    """Verify delete checks existence before deleting from bucket."""
    mock_client = MagicMock()
    storage = S3Storage(bucket_name="test-bucket", s3_client=mock_client)

    # 1. Existing file
    mock_client.head_object.return_value = {"ContentLength": 50}
    assert storage.delete("file_to_del.pdf") is True
    mock_client.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="file_to_del.pdf",
    )

    # 2. Non-existent file
    mock_client.reset_mock()
    error_response: Any = {
        "Error": {"Code": "NoSuchKey", "Message": "Not Found"},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }
    mock_client.head_object.side_effect = ClientError(error_response, "HeadObject")
    assert storage.delete("nonexistent.pdf") is False
    mock_client.delete_object.assert_not_called()


def test_get_storage_factory_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that get_storage returns S3Storage when STORAGE_BACKEND=s3."""
    get_storage.cache_clear()
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    get_settings.cache_clear()

    storage = get_storage()
    assert isinstance(storage, S3Storage)
    assert storage.bucket_name == "pm-documents"

    # Reset cache back to default
    get_storage.cache_clear()
    get_settings.cache_clear()
