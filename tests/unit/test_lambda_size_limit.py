# Tests for Lambda size limit handler
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest
from lambdas.size_limit.handler import (
    DEFAULT_MAX_SIZE_BYTES,
    calculate_project_total_size,
    get_s3_client,
    lambda_handler,
    send_api_callback,
)


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


def test_lambda_handler_empty_records() -> None:
    result = lambda_handler({"Records": []})
    assert result == {"status": "ignored", "reason": "no_records"}


def test_lambda_handler_non_s3_record() -> None:
    event = {"Records": [{"eventSource": "aws:sqs"}]}
    result = lambda_handler(event)
    assert result == {"status": "completed", "results": []}


def test_lambda_handler_unmatched_key() -> None:
    event = _build_s3_event("pm-documents", "unknown/folder/file.pdf")
    result = lambda_handler(event)
    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "ignored"
    assert result["results"][0]["reason"] == "unmatched_key_pattern"


@patch("lambdas.size_limit.handler.send_api_callback")
@patch("lambdas.size_limit.handler.get_s3_client")
def test_lambda_handler_within_limit_accepted(
    mock_get_s3: MagicMock,
    mock_send_callback: MagicMock,
) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3

    # Mock S3 pagination returning 2 files totaling 15 MB
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "projects/1/10/first.pdf", "Size": 5 * 1024 * 1024},
                {"Key": "projects/1/11/second.pdf", "Size": 10 * 1024 * 1024},
            ]
        }
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    event = _build_s3_event("pm-documents", "projects/1/11/second.pdf", size=10 * 1024 * 1024)

    result = lambda_handler(event)

    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    res = result["results"][0]
    assert res["status"] == "accepted"
    assert res["project_id"] == 1
    assert res["document_id"] == 11
    assert res["total_size_bytes"] == 15 * 1024 * 1024
    assert res["limit_bytes"] == DEFAULT_MAX_SIZE_BYTES

    # delete_object must NOT be called when within quota
    mock_s3.delete_object.assert_not_called()

    # send_api_callback must be called with accepted status
    mock_send_callback.assert_called_once()
    payload = mock_send_callback.call_args[0][2]
    assert payload["status"] == "accepted"
    assert payload["total_size_bytes"] == 15 * 1024 * 1024


@patch("lambdas.size_limit.handler.send_api_callback")
@patch("lambdas.size_limit.handler.get_s3_client")
def test_lambda_handler_exceeded_limit_rejected(
    mock_get_s3: MagicMock,
    mock_send_callback: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3

    # Set custom limit of 20 MB via env var
    monkeypatch.setenv("MAX_PROJECT_SIZE_BYTES", str(20 * 1024 * 1024))
    monkeypatch.setenv("API_CALLBACK_URL", "http://localhost:8000/internal/lambda/quota-alert")
    monkeypatch.setenv("LAMBDA_CALLBACK_SECRET", "secret-test-token")

    # Files sum to 25 MB (exceeds 20 MB)
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "projects/42/101/existing.pdf", "Size": 15 * 1024 * 1024},
                {"Key": "projects/42/102/large.pdf", "Size": 10 * 1024 * 1024},
            ]
        }
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    event = _build_s3_event("pm-documents", "projects/42/102/large.pdf", size=10 * 1024 * 1024)

    result = lambda_handler(event)

    assert result["status"] == "completed"
    res = result["results"][0]
    assert res["status"] == "rejected"
    assert res["project_id"] == 42
    assert res["document_id"] == 102
    assert res["total_size_bytes"] == 25 * 1024 * 1024
    assert res["limit_bytes"] == 20 * 1024 * 1024

    # delete_object MUST be called to purge the offending object from S3
    mock_s3.delete_object.assert_called_once_with(
        Bucket="pm-documents",
        Key="projects/42/102/large.pdf",
    )

    # send_api_callback must be called with rejected status
    mock_send_callback.assert_called_once()
    payload = mock_send_callback.call_args[0][2]
    assert payload["status"] == "rejected"
    assert payload["project_id"] == 42
    assert payload["document_id"] == 102
    assert payload["total_size_bytes"] == 15 * 1024 * 1024  # excluding the deleted object


@patch("lambdas.size_limit.handler.send_api_callback")
@patch("lambdas.size_limit.handler.get_s3_client")
def test_lambda_handler_url_encoded_key_handling(
    mock_get_s3: MagicMock,
    mock_send_callback: MagicMock,
) -> None:
    mock_s3 = MagicMock()
    mock_get_s3.return_value = mock_s3

    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "projects/7/3/my report (v1).pdf", "Size": 500},
            ]
        }
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    # S3 encodes spaces as + or %20
    event = _build_s3_event(
        "pm-documents",
        "projects/7/3/my+report+%28v1%29.pdf",
        size=500,
    )

    result = lambda_handler(event)
    assert result["status"] == "completed"
    res = result["results"][0]
    assert res["status"] == "accepted"
    assert res["key"] == "projects/7/3/my report (v1).pdf"
    assert res["project_id"] == 7
    assert res["document_id"] == 3


def test_calculate_project_total_size_multi_page() -> None:
    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Size": 100}, {"Size": 200}]},
        {"Contents": [{"Size": 300}]},
        {},  # empty page
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    total = calculate_project_total_size(mock_s3, "test-bucket", 99)
    assert total == 600
    mock_paginator.paginate.assert_called_once_with(
        Bucket="test-bucket",
        Prefix="projects/99/",
    )


def test_send_api_callback_no_url() -> None:
    assert not send_api_callback("", "secret", {"test": 1})


@patch("urllib.request.urlopen")
def test_send_api_callback_success(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    success = send_api_callback(
        callback_url="http://api:8000/internal/callback",
        secret="test-secret",
        payload={"status": "accepted"},
    )
    assert success is True
    assert mock_urlopen.call_count == 1
    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "http://api:8000/internal/callback"
    assert req.headers["X-lambda-secret"] == "test-secret"
    assert req.headers["Content-type"] == "application/json"


@patch("urllib.request.urlopen")
def test_send_api_callback_failure(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = URLError("Connection refused")

    success = send_api_callback(
        callback_url="http://invalid-host/callback",
        secret="test-secret",
        payload={"status": "rejected"},
    )
    assert success is False


@patch("boto3.client")
def test_get_s3_client_with_custom_endpoint(
    mock_boto_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://localstack:4566")
    get_s3_client()
    mock_boto_client.assert_called_with("s3", endpoint_url="http://localstack:4566")

    # Explicit override takes precedence
    get_s3_client("http://custom:9000")
    mock_boto_client.assert_called_with("s3", endpoint_url="http://custom:9000")
