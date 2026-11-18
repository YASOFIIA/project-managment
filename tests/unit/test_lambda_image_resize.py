# Unit tests for Lambda image resize handler
from __future__ import annotations

import io
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from lambdas.image_resize.handler import (
    THUMB_MAX_SIZE,
    create_thumbnail,
    get_s3_client,
    lambda_handler,
)

# Minimal valid 1x1 PNG binary
MINIMAL_PNG_BYTES: bytes = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal valid 1x1 JPEG binary
MINIMAL_JPEG_BYTES: bytes = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
    b"\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01"
    b"\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01"
    b"\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08"
    b"\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd5\xff\xd9"
)


@pytest.fixture
def png_bytes() -> bytes:
    return MINIMAL_PNG_BYTES


@pytest.fixture
def jpeg_bytes() -> bytes:
    return MINIMAL_JPEG_BYTES


def _build_s3_event(bucket: str, key: str, size: int = 1024) -> dict[str, Any]:
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key, "size": size},
                },
            }
        ]
    }


# 1. Test that PNG image is resized and thumbnail uploaded
@patch("lambdas.image_resize.handler.get_s3_client")
def test_png_image_resized_and_thumbnail_uploaded(
    mock_get_s3: MagicMock,
    png_bytes: bytes,
) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3
    mock_s3.get_object.return_value = {"Body": io.BytesIO(png_bytes)}

    event = _build_s3_event("pm-documents", "projects/1/10/diagram.png", size=len(png_bytes))
    result = lambda_handler(event)

    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    res = result["results"][0]
    assert res["status"] == "resized"
    assert res["project_id"] == 1
    assert res["document_id"] == 10
    assert res["key"] == "projects/1/10/diagram.png"
    assert res["thumbnail_key"] == "projects/1/10/thumb_diagram.png"
    assert res["format"] == "PNG"

    mock_s3.get_object.assert_called_once_with(
        Bucket="pm-documents",
        Key="projects/1/10/diagram.png",
    )
    mock_s3.put_object.assert_called_once()
    put_kwargs = mock_s3.put_object.call_args.kwargs
    assert put_kwargs["Bucket"] == "pm-documents"
    assert put_kwargs["Key"] == "projects/1/10/thumb_diagram.png"
    assert put_kwargs["ContentType"] == "image/png"
    assert put_kwargs["Body"].startswith(b"\x89PNG\r\n\x1a\n")


# 2. Test that JPEG image (.jpg and .jpeg) is resized and thumbnail uploaded
@pytest.mark.parametrize("filename", ["photo.jpg", "banner.JPEG"])
@patch("lambdas.image_resize.handler.get_s3_client")
def test_jpeg_image_resized_and_thumbnail_uploaded(
    mock_get_s3: MagicMock,
    jpeg_bytes: bytes,
    filename: str,
) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3
    mock_s3.get_object.return_value = {"Body": io.BytesIO(jpeg_bytes)}

    key = f"projects/5/22/{filename}"
    event = _build_s3_event("pm-documents", key, size=len(jpeg_bytes))
    result = lambda_handler(event)

    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    res = result["results"][0]
    assert res["status"] == "resized"
    assert res["project_id"] == 5
    assert res["document_id"] == 22
    assert res["thumbnail_key"] == f"projects/5/22/thumb_{filename}"
    assert res["format"] == "JPEG"

    mock_s3.put_object.assert_called_once()
    put_kwargs = mock_s3.put_object.call_args.kwargs
    assert put_kwargs["Bucket"] == "pm-documents"
    assert put_kwargs["Key"] == f"projects/5/22/thumb_{filename}"
    assert put_kwargs["ContentType"] == "image/jpeg"
    assert put_kwargs["Body"].startswith(b"\xff\xd8\xff")


# 3. Test that non-image files (PDF, DOCX) are skipped
@pytest.mark.parametrize(
    "filename",
    ["specification.pdf", "architecture.docx", "notes.txt"],
)
@patch("lambdas.image_resize.handler.get_s3_client")
def test_non_image_files_skipped(
    mock_get_s3: MagicMock,
    filename: str,
) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3

    key = f"projects/2/15/{filename}"
    event = _build_s3_event("pm-documents", key)
    result = lambda_handler(event)

    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    assert result["results"][0] == {
        "status": "skipped",
        "key": key,
        "reason": "not_an_image",
    }
    mock_s3.get_object.assert_not_called()
    mock_s3.put_object.assert_not_called()


# 4. Test that unmatched S3 key patterns are skipped
@patch("lambdas.image_resize.handler.get_s3_client")
def test_unmatched_s3_key_pattern_skipped(mock_get_s3: MagicMock) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3

    event = _build_s3_event("pm-documents", "uploads/raw/avatar.png")
    result = lambda_handler(event)

    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    assert result["results"][0] == {
        "status": "ignored",
        "key": "uploads/raw/avatar.png",
        "reason": "unmatched_key_pattern",
    }
    mock_s3.get_object.assert_not_called()
    mock_s3.put_object.assert_not_called()


# 5. Test that empty event records are handled gracefully
def test_empty_event_records_handled_gracefully() -> None:
    assert lambda_handler({}) == {"status": "ignored", "reason": "no_records"}
    assert lambda_handler({"Records": []}) == {"status": "ignored", "reason": "no_records"}


# 6. Test thumbnail key is thumb_<original_filename> and PIL.Image.thumbnail((200, 200)) is called
@patch("lambdas.image_resize.handler.Image")
@patch("lambdas.image_resize.handler.get_s3_client")
def test_thumbnail_key_and_pil_image_interaction(
    mock_get_s3: MagicMock,
    mock_pil_image: MagicMock,
    png_bytes: bytes,
) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3
    mock_s3.get_object.return_value = {"Body": io.BytesIO(png_bytes)}

    mock_img_instance = MagicMock()

    def fake_save(buf: io.BytesIO, format: str | None = None) -> None:
        buf.write(b"fake-resized-png-bytes")

    mock_img_instance.save.side_effect = fake_save
    mock_pil_image.open.return_value = mock_img_instance

    event = _build_s3_event("pm-documents", "projects/42/99/wireframe_v2.png")
    result = lambda_handler(event)

    assert result["status"] == "completed"
    res = result["results"][0]
    assert res["thumbnail_key"] == "projects/42/99/thumb_wireframe_v2.png"

    mock_pil_image.open.assert_called_once()
    mock_img_instance.thumbnail.assert_called_once_with((200, 200))
    mock_img_instance.save.assert_called_once()
    assert mock_img_instance.save.call_args.kwargs["format"] == "PNG"

    mock_s3.put_object.assert_called_once_with(
        Bucket="pm-documents",
        Key="projects/42/99/thumb_wireframe_v2.png",
        Body=b"fake-resized-png-bytes",
        ContentType="image/png",
    )


# Test skipping already-generated thumbnails to avoid infinite S3 trigger loops
@patch("lambdas.image_resize.handler.get_s3_client")
def test_existing_thumbnail_is_skipped(mock_get_s3: MagicMock) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3

    event = _build_s3_event("pm-documents", "projects/1/10/thumb_diagram.png")
    result = lambda_handler(event)

    assert result["status"] == "completed"
    assert result["results"][0] == {
        "status": "skipped",
        "key": "projects/1/10/thumb_diagram.png",
        "reason": "already_thumbnail",
    }
    mock_s3.get_object.assert_not_called()
    mock_s3.put_object.assert_not_called()


# Test graceful error handling when S3 download or image processing fails
@patch("lambdas.image_resize.handler.get_s3_client")
def test_s3_or_image_error_handled_gracefully(mock_get_s3: MagicMock) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3
    mock_s3.get_object.side_effect = RuntimeError("S3 connection timeout")

    event = _build_s3_event("pm-documents", "projects/3/7/broken.png")
    result = lambda_handler(event)

    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "error"
    assert result["results"][0]["key"] == "projects/3/7/broken.png"
    assert "S3 connection timeout" in result["results"][0]["reason"]
    mock_s3.put_object.assert_not_called()


# Test create_thumbnail helper directly with PNG and JPEG bytes
def test_create_thumbnail_helper(png_bytes: bytes, jpeg_bytes: bytes) -> None:
    assert THUMB_MAX_SIZE == (200, 200)
    png_thumb = create_thumbnail(png_bytes, ".png")
    assert png_thumb.startswith(b"\x89PNG\r\n\x1a\n")

    jpg_thumb = create_thumbnail(jpeg_bytes, ".jpg")
    assert jpg_thumb.startswith(b"\xff\xd8\xff")


# Test get_s3_client respects S3_ENDPOINT_URL and explicit override
@patch("boto3.client")
def test_get_s3_client_endpoint(
    mock_boto_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://localstack:4566")
    get_s3_client()
    mock_boto_client.assert_called_with("s3", endpoint_url="http://localstack:4566")

    get_s3_client("http://custom:9000")
    mock_boto_client.assert_called_with("s3", endpoint_url="http://custom:9000")
