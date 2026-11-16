# E2E tests for LocalStack S3 and Lambda workflow
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
from app.domain.roles import ProjectRole
from app.models.document import Document
from tests.factories import create_document, create_project, create_project_member, create_user


# Check the lambda packaging creates a valid zip containing handler.py
def test_lambda_zip_packaging_integrity() -> None:
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


# Check deploy-lambda-localstack.sh and init-localstack.sh exist with proper permissions
def test_deploy_scripts_exist_and_are_executable() -> None:
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


# Simulate complete E2E workflow: S3 upload within limit -> Lambda event -> API callback
def test_end_to_end_s3_upload_within_limit_syncs_db(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    key = doc.stored_filename

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


# Simulate E2E workflow when quota is exceeded: Lambda deletes S3 file and purges DB record
def test_end_to_end_s3_upload_exceeding_limit_purges_s3_and_db(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    key = doc.stored_filename

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


# Check upload via API with S3Storage
def test_api_upload_with_s3_storage_and_lambda_lifecycle(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.security import create_access_token
    from app.main import app
    from app.storage import get_storage as orig_get_storage
    from app.storage.s3 import S3Storage
    from tests.integration.test_s3_storage_integration import _build_mock_s3_client

    mock_client, in_memory_s3 = _build_mock_s3_client()
    s3_storage = S3Storage(bucket_name="pm-documents", s3_client=mock_client)
    app.dependency_overrides[orig_get_storage] = lambda: s3_storage

    settings = get_settings()
    monkeypatch.setenv("API_CALLBACK_URL", "http://testserver/internal/lambda/quota-alert")
    monkeypatch.setenv("LAMBDA_CALLBACK_SECRET", settings.lambda_callback_secret)

    def fake_send_callback(
        url: str, secret: str, payload: dict[str, Any], timeout_seconds: float = 5.0
    ) -> bool:
        resp = client.post(
            "/internal/lambda/quota-alert", json=payload, headers={"X-Lambda-Secret": secret}
        )
        return bool(resp.status_code == 200)

    try:
        user = create_user(db_session, login="s3_api_user")
        token = create_access_token(user_id=user.id, login=user.login)
        headers = {"Authorization": f"Bearer {token}"}

        project = create_project(db_session, name="S3 API Lambda Project")
        create_project_member(
            db_session, project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
        )

        pdf_bytes = b"%PDF-1.4 Initial Valid Cloud Spec"

        # 1. Upload file through API
        resp = client.post(
            f"/project/{project.id}/documents",
            files=[("files", ("spec.pdf", pdf_bytes, "application/pdf"))],
            headers=headers,
        )
        assert resp.status_code == 201
        doc_id = resp.json()[0]["id"]

        # Check canonical S3 key
        doc_record = db_session.get(Document, doc_id)
        assert doc_record is not None
        expected_key = doc_record.stored_filename
        assert f"pm-documents/{expected_key}" in in_memory_s3
        assert s3_storage.exists(expected_key) is True

        # S3 triggers Lambda event for created object
        s3_event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {"name": "pm-documents"},
                        "object": {"key": expected_key, "size": len(pdf_bytes)},
                    },
                }
            ]
        }

        # Mock list_objects_v2 in Lambda to return current S3 objects
        mock_lambda_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": expected_key, "Size": len(pdf_bytes)}]}
        ]
        mock_lambda_s3.get_paginator.return_value = mock_paginator

        with (
            patch("lambdas.size_limit.handler.get_s3_client", return_value=mock_lambda_s3),
            patch("lambdas.size_limit.handler.send_api_callback", side_effect=fake_send_callback),
        ):
            lambda_res = lambda_handler(s3_event)

        assert lambda_res["status"] == "completed"
        assert lambda_res["results"][0]["status"] == "accepted"
        mock_lambda_s3.delete_object.assert_not_called()
        assert s3_storage.exists(expected_key) is True

        # 2. Exceed limit scenario -> Lambda rejects, deletes S3 object, and purges DB row
        huge_bytes = b"%PDF-1.4 " + b"X" * 1024
        resp2 = client.post(
            f"/project/{project.id}/documents",
            files=[("files", ("huge.pdf", huge_bytes, "application/pdf"))],
            headers=headers,
        )
        assert resp2.status_code == 201
        huge_doc_id = resp2.json()[0]["id"]
        huge_doc_record = db_session.get(Document, huge_doc_id)
        assert huge_doc_record is not None
        huge_key = huge_doc_record.stored_filename
        assert s3_storage.exists(huge_key) is True

        huge_event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {"name": "pm-documents"},
                        "object": {"key": huge_key, "size": len(huge_bytes)},
                    },
                }
            ]
        }

        # Configure Lambda limit so that this object exceeds quota
        monkeypatch.setenv("MAX_PROJECT_SIZE_BYTES", str(len(pdf_bytes)))
        mock_lambda_s3_reject = MagicMock()
        mock_paginator_reject = MagicMock()
        # Sum is len(pdf_bytes) + len(huge_bytes) > MAX_PROJECT_SIZE_BYTES
        mock_paginator_reject.paginate.return_value = [
            {
                "Contents": [
                    {"Key": expected_key, "Size": len(pdf_bytes)},
                    {"Key": huge_key, "Size": len(huge_bytes)},
                ]
            }
        ]
        mock_lambda_s3_reject.get_paginator.return_value = mock_paginator_reject

        with (
            patch("lambdas.size_limit.handler.get_s3_client", return_value=mock_lambda_s3_reject),
            patch("lambdas.size_limit.handler.send_api_callback", side_effect=fake_send_callback),
        ):
            lambda_res_reject = lambda_handler(huge_event)

        assert lambda_res_reject["status"] == "completed"
        assert lambda_res_reject["results"][0]["status"] == "rejected"
        mock_lambda_s3_reject.delete_object.assert_called_once_with(
            Bucket="pm-documents", Key=huge_key
        )
        # Verify DB document was purged by the callback
        assert db_session.get(Document, huge_doc_id) is None
        # Original document still exists
        assert db_session.get(Document, doc_id) is not None

    finally:
        app.dependency_overrides.pop(orig_get_storage, None)
