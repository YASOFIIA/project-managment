# Lambda handler for document size quota checks
from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from typing import Any

import boto3

logger = logging.getLogger("lambdas.size_limit")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

DEFAULT_MAX_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
S3_KEY_PATTERN = re.compile(r"^projects/(?P<project_id>\d+)/(?P<document_id>\d+)/(?P<filename>.+)$")


# Create boto3 S3 client
def get_s3_client(endpoint_url: str | None = None) -> Any:
    endpoint = endpoint_url or os.getenv("S3_ENDPOINT_URL") or None
    return boto3.client("s3", endpoint_url=endpoint)


# Send webhook to internal API callback
def send_api_callback(
    callback_url: str,
    secret: str,
    payload: dict[str, Any],
    timeout_seconds: float = 5.0,
) -> bool:
    if not callback_url:
        logger.info("API_CALLBACK_URL is not configured; skipping callback dispatch.")
        return False

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=callback_url,
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "X-Lambda-Secret": secret,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = response.getcode()
            logger.info("API callback to %s succeeded with HTTP %d", callback_url, status_code)
            return bool(200 <= status_code < 300)
    except Exception as exc:
        logger.error("API callback to %s failed: %s", callback_url, exc)
        return False


# Sum sizes of all objects in project prefix
def calculate_project_total_size(s3_client: Any, bucket: str, project_id: int) -> int:
    prefix = f"projects/{project_id}/"
    total_size = 0
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        contents = page.get("Contents", [])
        for item in contents:
            total_size += item.get("Size", 0)

    return total_size


# Lambda entrypoint for S3 ObjectCreated events
def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    logger.info("Lambda size_limit invoked with event: %s", json.dumps(event))

    records = event.get("Records", [])
    if not records:
        logger.warning("Event contains no Records. Skipping processing.")
        return {"status": "ignored", "reason": "no_records"}

    max_size_bytes = int(os.getenv("MAX_PROJECT_SIZE_BYTES", str(DEFAULT_MAX_SIZE_BYTES)))
    callback_url = os.getenv("API_CALLBACK_URL", "")
    callback_secret = os.getenv("LAMBDA_CALLBACK_SECRET", "")
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

        # Compute current project total size across all stored objects
        total_size = calculate_project_total_size(s3_client, bucket_name, project_id)
        logger.info(
            "Project %d total size is %d bytes (limit: %d bytes)",
            project_id,
            total_size,
            max_size_bytes,
        )

        if total_size > max_size_bytes:
            logger.warning(
                "Project %d exceeded size limit (%d > %d). Deleting offending object: %s",
                project_id,
                total_size,
                max_size_bytes,
                key,
            )
            s3_client.delete_object(Bucket=bucket_name, Key=key)

            callback_payload = {
                "project_id": project_id,
                "document_id": document_id,
                "filename": filename,
                "status": "rejected",
                "total_size_bytes": max(0, total_size - s3_info["object"].get("size", 0)),
                "limit_bytes": max_size_bytes,
            }
            send_api_callback(callback_url, callback_secret, callback_payload)

            processed_results.append(
                {
                    "status": "rejected",
                    "project_id": project_id,
                    "document_id": document_id,
                    "key": key,
                    "total_size_bytes": total_size,
                    "limit_bytes": max_size_bytes,
                }
            )
        else:
            callback_payload = {
                "project_id": project_id,
                "document_id": document_id,
                "filename": filename,
                "status": "accepted",
                "total_size_bytes": total_size,
                "limit_bytes": max_size_bytes,
            }
            send_api_callback(callback_url, callback_secret, callback_payload)

            processed_results.append(
                {
                    "status": "accepted",
                    "project_id": project_id,
                    "document_id": document_id,
                    "key": key,
                    "total_size_bytes": total_size,
                    "limit_bytes": max_size_bytes,
                }
            )

    return {"status": "completed", "results": processed_results}
