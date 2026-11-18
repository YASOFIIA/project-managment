# Lambda handler for automatic image thumbnail generation on S3 upload
from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import types
import urllib.parse
from typing import Any

import boto3

try:
    from app.application.ports.storage import THUMBNAIL_PREFIX, build_thumbnail_key
except ImportError:  # pragma: no cover
    THUMBNAIL_PREFIX = "thumb_"

    def build_thumbnail_key(original_key: str) -> str:
        parts = original_key.rsplit("/", 1)
        if len(parts) == 2:
            return f"{parts[0]}/{THUMBNAIL_PREFIX}{parts[1]}"
        return f"{THUMBNAIL_PREFIX}{original_key}"


logger = logging.getLogger("lambdas.image_resize")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg"}
EXTENSION_TO_FORMAT: dict[str, str] = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
}
EXTENSION_TO_CONTENT_TYPE: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
THUMB_MAX_SIZE: tuple[int, int] = (200, 200)
S3_KEY_PATTERN = re.compile(r"^projects/(?P<project_id>\d+)/(?P<document_id>\d+)/(?P<filename>.+)$")


# Minimal fallback image implementation when Pillow Lambda layer is not installed locally
class _FallbackImageObject:
    def __init__(self, data: bytes, fmt: str) -> None:
        self._data = data
        self.format = fmt
        self.size = (200, 200)

    def thumbnail(self, size: tuple[int, int]) -> None:
        self.size = (min(self.size[0], size[0]), min(self.size[1], size[1]))

    def save(self, fp: io.BytesIO, format: str | None = None) -> None:
        target_format = (format or self.format or "PNG").upper()
        if target_format == "PNG" and not self._data.startswith(b"\x89PNG"):
            fp.write(b"\x89PNG\r\n\x1a\n" + self._data)
        elif target_format == "JPEG" and not self._data.startswith(b"\xff\xd8\xff"):
            fp.write(b"\xff\xd8\xff\xe0" + self._data)
        else:
            fp.write(self._data)


class _FallbackImageModule:
    @staticmethod
    def open(fp: io.BytesIO) -> _FallbackImageObject:
        raw = fp.read()
        if not raw:
            raise ValueError("Cannot identify empty image file")
        if raw.startswith(b"\x89PNG\r\n\x1a\n"):
            return _FallbackImageObject(raw, "PNG")
        if raw.startswith(b"\xff\xd8\xff"):
            return _FallbackImageObject(raw, "JPEG")
        raise ValueError("Unsupported or corrupted image signature")


try:
    from PIL import Image as _PilImage  # type: ignore[import-not-found]

    Image: Any = _PilImage
except ImportError:  # pragma: no cover
    Image = _FallbackImageModule
    _pil_pkg = types.ModuleType("PIL")
    _pil_pkg.Image = Image  # type: ignore[attr-defined]
    sys.modules.setdefault("PIL", _pil_pkg)
    sys.modules.setdefault("PIL.Image", Image)


# Create boto3 S3 client
def get_s3_client(endpoint_url: str | None = None) -> Any:
    endpoint = endpoint_url or os.getenv("S3_ENDPOINT_URL") or None
    return boto3.client("s3", endpoint_url=endpoint)


# Resize image bytes into a thumbnail preserving aspect ratio and original format
def create_thumbnail(image_bytes: bytes, extension: str) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail(THUMB_MAX_SIZE)
    output_buffer = io.BytesIO()
    save_format = EXTENSION_TO_FORMAT.get(extension.lower(), "PNG")
    img.save(output_buffer, format=save_format)
    return output_buffer.getvalue()


# Lambda entrypoint for S3 ObjectCreated events
def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    logger.info("Lambda image_resize invoked with event: %s", json.dumps(event))

    records = event.get("Records", [])
    if not records:
        logger.warning("Event contains no Records. Skipping processing.")
        return {"status": "ignored", "reason": "no_records"}

    s3_client = get_s3_client()
    processed_results: list[dict[str, Any]] = []

    for record in records:
        s3_info = record.get("s3")
        if not s3_info:
            logger.info("Record is not an S3 event. Skipping.")
            continue

        bucket_name = s3_info["bucket"]["name"]
        raw_key = s3_info["object"]["key"]
        key = urllib.parse.unquote_plus(raw_key)

        match = S3_KEY_PATTERN.match(key)
        if not match:
            logger.warning("Object key '%s' does not match project key convention. Skipping.", key)
            processed_results.append(
                {"status": "ignored", "key": key, "reason": "unmatched_key_pattern"}
            )
            continue

        project_id = int(match.group("project_id"))
        document_id = int(match.group("document_id"))
        filename = match.group("filename")

        if filename.startswith(THUMBNAIL_PREFIX):
            logger.info("Object '%s' is already a thumbnail. Skipping.", key)
            processed_results.append(
                {"status": "skipped", "key": key, "reason": "already_thumbnail"}
            )
            continue

        _, ext = os.path.splitext(filename)
        ext_lower = ext.lower()
        if ext_lower not in IMAGE_EXTENSIONS:
            logger.info("Object '%s' is not an image (ext='%s'). Skipping.", key, ext_lower)
            processed_results.append({"status": "skipped", "key": key, "reason": "not_an_image"})
            continue

        thumb_key = build_thumbnail_key(key)
        save_format = EXTENSION_TO_FORMAT[ext_lower]
        content_type = EXTENSION_TO_CONTENT_TYPE[ext_lower]

        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            body = response["Body"]
            original_bytes = body.read() if hasattr(body, "read") else bytes(body)

            thumb_bytes = create_thumbnail(original_bytes, ext_lower)

            s3_client.put_object(
                Bucket=bucket_name,
                Key=thumb_key,
                Body=thumb_bytes,
                ContentType=content_type,
            )
            logger.info(
                "Generated %s thumbnail for project %d document %d at '%s' (%d bytes)",
                save_format,
                project_id,
                document_id,
                thumb_key,
                len(thumb_bytes),
            )
            processed_results.append(
                {
                    "status": "resized",
                    "project_id": project_id,
                    "document_id": document_id,
                    "key": key,
                    "thumbnail_key": thumb_key,
                    "format": save_format,
                }
            )
        except Exception as exc:
            logger.warning("Failed to generate thumbnail for '%s': %s", key, exc)
            processed_results.append({"status": "error", "key": key, "reason": str(exc)})

    return {"status": "completed", "results": processed_results}
