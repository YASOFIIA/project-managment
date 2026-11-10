"""End-to-end integration tests for LocalStack S3 + Lambda size limit workflow."""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from lambdas.size_limit.handler import lambda_handler
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document
from app.models.project import ProjectRole
from app.storage.s3 import format_s3_key
from tests.factories import create_document, create_project, create_project_member, create_user


def test_lambda_zip_packaging_integrity() -> None:
    """Verify the lambda packaging creates a valid zip containing handler.py."""
    lambda_dir = Path(__file__).resolve().parents[2] / "lambdas" / "size_limit"
    handler_file = lambda_dir / "handler.py"
    assert handler_file.exists(), f"Handler file missing at {handler_file}"

    # Create in-memory zip bundle
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(handler_file, arcname="handler.py")

    zip_buffer.seek(0)
    with zipfile.ZipFile(zip_buffer, mode="r") as zf:
        namelist = zf.namelist()
        assert "handler.py" in namelist
        content = zf.read("handler.py").decode("utf-8")
        assert "def lambda_handler(" in content


def test_deploy_scripts_exist_and_are_executable() -> None:
    """Verify deploy-lambda-localstack.sh and init-localstack.sh exist with proper permissions."""
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    init_script = scripts_dir / "init-localstack.sh"
    deploy_script = scripts_dir / "deploy-lambda-localstack.sh"

    assert init_script.exists()
    assert deploy_script.exists()
    assert os.access(init_script, os.X_OK)
    assert os.access(deploy_script, os.X_OK)

    init_content = init_script.read_text()
    assert "pm-size-limit" in init_content
    assert "put-bucket-notification-configuration" in init_content


def test_end_to_end_s3_upload_within_limit_syncs_db(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate complete E2E workflow: S3 upload within limit -> Lambda event -> API callback."""
    settings = get_settings()
    user = create_user(db_session)
    project = create_project(db_session, total_size_bytes=1000)
    create_project_member(
        db_session, project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
    )
    doc = create_document(
        db_session, project_id=project.id, filename="spec.pdf", file_size_bytes=4000
    )

    bucket = "pm-documents"
    key = format_s3_key(project.id, doc.id, doc.filename)

    mock_s3 = MagicMock()
    # Paginator returns files totaling 5000 bytes (1000 + 4000)
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{"Contents": [{"Key": key, "Size": 5000}]}]
    mock_s3.get_paginator.return_value = mock_paginator

    # Wire mock callback to invoke TestClient /internal/lambda/quota-alert directly
    def fake_send_callback(
        url: str, secret: str, payload: dict[str, Any], timeout_seconds: float = 5.0
    ) -> bool:
        resp = client.post(
            "/internal/lambda/quota-alert",
            json=payload,
            headers={"X-Lambda-Secret": secret},
        )
        return bool(resp.status_code == 200)

    s3_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key, "size": 4000},
                },
            }
        ]
    }

    monkeypatch.setenv("API_CALLBACK_URL", "http://testserver/internal/lambda/quota-alert")
    monkeypatch.setenv("LAMBDA_CALLBACK_SECRET", settings.lambda_callback_secret)

    with (
        patch("lambdas.size_limit.handler.get_s3_client", return_value=mock_s3),
        patch("lambdas.size_limit.handler.send_api_callback", side_effect=fake_send_callback),
    ):
        result = lambda_handler(s3_event)

    assert result["status"] == "completed"
    assert result["results"][0]["status"] == "accepted"

    # Verify S3 delete was NOT invoked
    mock_s3.delete_object.assert_not_called()

    # Verify DB state was updated with new total_size_bytes
    db_session.refresh(project)
    assert project.total_size_bytes == 5000

    # Document still in DB
    assert db_session.get(Document, doc.id) is not None


def test_end_to_end_s3_upload_exceeding_limit_purges_s3_and_db(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate E2E workflow when quota is exceeded: Lambda deletes S3 file and purges DB record."""
    settings = get_settings()
    user = create_user(db_session)
    # Existing project already near limit
    project = create_project(db_session, total_size_bytes=50_000_000)
    create_project_member(
        db_session, project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
    )
    # New document pushes total to 60 MB
    doc = create_document(
        db_session, project_id=project.id, filename="huge_video.mp4", file_size_bytes=10_000_000
    )

    bucket = "pm-documents"
    key = format_s3_key(project.id, doc.id, doc.filename)

    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": "existing.pdf", "Size": 50_000_000},
                {"Key": key, "Size": 10_000_000},
            ]
        }
    ]
    mock_s3.get_paginator.return_value = mock_paginator

    def fake_send_callback(
        url: str, secret: str, payload: dict[str, Any], timeout_seconds: float = 5.0
    ) -> bool:
        resp = client.post(
            "/internal/lambda/quota-alert",
            json=payload,
            headers={"X-Lambda-Secret": secret},
        )
        return bool(resp.status_code == 200)

    s3_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key, "size": 10_000_000},
                },
            }
        ]
    }

    monkeypatch.setenv("API_CALLBACK_URL", "http://testserver/internal/lambda/quota-alert")
    monkeypatch.setenv("LAMBDA_CALLBACK_SECRET", settings.lambda_callback_secret)

    with (
        patch("lambdas.size_limit.handler.get_s3_client", return_value=mock_s3),
        patch("lambdas.size_limit.handler.send_api_callback", side_effect=fake_send_callback),
    ):
        result = lambda_handler(s3_event)

    assert result["status"] == "completed"
    assert result["results"][0]["status"] == "rejected"

    # Offending object was deleted from S3
    mock_s3.delete_object.assert_called_once_with(Bucket=bucket, Key=key)

    # Offending document was purged from database
    purged_doc = db_session.get(Document, doc.id)
    assert purged_doc is None

    # Project size preserved at 50 MB
    db_session.refresh(project)
    assert project.total_size_bytes == 50_000_000
