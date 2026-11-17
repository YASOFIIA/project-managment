# Integration tests for S3 image upload and Lambda thumbnail generation
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from lambdas.image_resize.handler import lambda_handler as image_resize_handler
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.domain.roles import ProjectRole
from app.models.document import Document
from app.storage import get_storage as orig_get_storage
from app.storage.s3 import S3Storage
from tests.factories import create_project, create_project_member, create_user
from tests.integration.test_s3_storage_integration import _build_mock_s3_client
from tests.unit.test_lambda_image_resize import MINIMAL_PNG_BYTES


# Verify uploading an image to a project and running image_resize Lambda creates the thumbnail
def test_upload_image_and_generate_thumbnail_in_s3(
    client: TestClient,
    db_session: Session,
) -> None:
    from app.main import app

    mock_client, in_memory_s3 = _build_mock_s3_client()
    s3_storage = S3Storage(bucket_name="pm-documents", s3_client=mock_client)
    app.dependency_overrides[orig_get_storage] = lambda: s3_storage

    try:
        user = create_user(db_session, login="img_resize_owner", email="img_owner@example.com")
        token = create_access_token(user_id=user.id, login=user.login)
        headers = {"Authorization": f"Bearer {token}"}

        project = create_project(db_session, name="Image Thumbnail Project")
        create_project_member(
            db_session,
            project_id=project.id,
            user_id=user.id,
            role=ProjectRole.OWNER,
        )

        # 1. Upload PNG image through the API
        resp = client.post(
            f"/project/{project.id}/documents",
            files=[("files", ("architecture.png", MINIMAL_PNG_BYTES, "image/png"))],
            headers=headers,
        )
        assert resp.status_code == 201
        doc_id = resp.json()[0]["id"]

        doc_record = db_session.get(Document, doc_id)
        assert doc_record is not None
        original_key = doc_record.stored_filename
        assert s3_storage.exists(original_key) is True

        # 2. Simulate S3 ObjectCreated event triggering image_resize Lambda
        s3_event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {"name": "pm-documents"},
                        "object": {"key": original_key, "size": len(MINIMAL_PNG_BYTES)},
                    },
                }
            ]
        }

        with patch("lambdas.image_resize.handler.get_s3_client", return_value=mock_client):
            lambda_res = image_resize_handler(s3_event)

        assert lambda_res["status"] == "completed"
        assert len(lambda_res["results"]) == 1
        assert lambda_res["results"][0]["status"] == "resized"

        stored_basename = Path(original_key).name
        expected_thumb_key = f"projects/{project.id}/{doc_id}/thumb_{stored_basename}"
        assert lambda_res["results"][0]["thumbnail_key"] == expected_thumb_key

        # 3. Verify thumbnail exists at expected S3 key
        assert f"pm-documents/{expected_thumb_key}" in in_memory_s3
        assert s3_storage.exists(expected_thumb_key) is True
        thumb_bytes = in_memory_s3[f"pm-documents/{expected_thumb_key}"]
        assert thumb_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        app.dependency_overrides.pop(orig_get_storage, None)
