import io
from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.application.ports.storage import format_s3_key
from app.core.security import create_access_token
from app.domain.roles import ProjectRole
from app.models.document import Document
from app.storage.s3 import S3Storage
from tests.factories import create_project, create_project_member, create_user


def _build_mock_s3_client() -> tuple[MagicMock, dict[str, bytes]]:
    """Create an in-memory mocked S3 client simulating put, get, head, delete."""
    in_memory: dict[str, bytes] = {}

    def mock_put_object(
        Bucket: str, Key: str, Body: bytes | io.BytesIO, **kwargs: object
    ) -> dict[str, object]:
        payload = Body if isinstance(Body, bytes) else Body.read()
        in_memory[f"{Bucket}/{Key}"] = payload
        return {"ETag": "dummy-etag"}

    def mock_get_object(Bucket: str, Key: str, **kwargs: object) -> dict[str, object]:
        full_key = f"{Bucket}/{Key}"
        if full_key not in in_memory:
            err_dict: Any = {
                "Error": {"Code": "NoSuchKey", "Message": "Key not found"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            }
            raise ClientError(err_dict, "GetObject")
        return {"Body": io.BytesIO(in_memory[full_key])}

    def mock_head_object(Bucket: str, Key: str, **kwargs: object) -> dict[str, object]:
        full_key = f"{Bucket}/{Key}"
        if full_key not in in_memory:
            err_dict: Any = {
                "Error": {"Code": "404", "Message": "Not found"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            }
            raise ClientError(err_dict, "HeadObject")
        return {"ContentLength": len(in_memory[full_key])}

    def mock_delete_object(Bucket: str, Key: str, **kwargs: object) -> dict[str, object]:
        in_memory.pop(f"{Bucket}/{Key}", None)
        return {}

    mock_client = MagicMock()
    mock_client.put_object.side_effect = mock_put_object
    mock_client.get_object.side_effect = mock_get_object
    mock_client.head_object.side_effect = mock_head_object
    mock_client.delete_object.side_effect = mock_delete_object
    return mock_client, in_memory


def test_s3_storage_lifecycle_with_s3_key_format() -> None:
    """Verify S3Storage operations using projects/<project_id>/<document_id>/<name> layout."""
    mock_client, _ = _build_mock_s3_client()
    storage = S3Storage(bucket_name="pm-documents", s3_client=mock_client)

    # 1. Format S3 key according to canonical layout
    s3_key = format_s3_key(project_id=42, document_id=101, filename="quarterly_report.pdf")
    assert s3_key == "projects/42/101/quarterly_report.pdf"

    # 2. Save
    file_bytes = b"%PDF-1.4 Q3 Financial Performance"
    saved_key = storage.save(s3_key, file_bytes)
    assert saved_key == s3_key
    assert storage.exists(s3_key) is True

    # 3. Stream download
    stream = storage.get(s3_key)
    assert stream.read() == file_bytes

    # 4. Delete
    assert storage.delete(s3_key) is True
    assert storage.exists(s3_key) is False
    assert storage.delete(s3_key) is False

    with pytest.raises(FileNotFoundError):
        storage.get(s3_key)


def test_api_integration_with_s3_storage_backend(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify FastAPI endpoints seamlessly function when S3Storage is the active backend."""
    mock_client, _ = _build_mock_s3_client()
    s3_storage = S3Storage(bucket_name="pm-documents", s3_client=mock_client)

    # Override get_storage dependency in FastAPI app
    from app.main import app
    from app.storage import get_storage as original_get_storage

    app.dependency_overrides[original_get_storage] = lambda: s3_storage

    try:
        user = create_user(db_session, login="s3_tester")
        token = create_access_token(user_id=user.id, login=user.login)
        headers = {"Authorization": f"Bearer {token}"}

        project = create_project(db_session, name="S3 Cloud Project")
        create_project_member(
            db_session,
            project_id=project.id,
            user_id=user.id,
            role=ProjectRole.OWNER,
        )

        pdf_bytes = b"%PDF-1.4 Cloud Native Architecture Plan"

        # 1. Upload via API
        upload_resp = client.post(
            f"/project/{project.id}/documents",
            files=[("files", ("cloud_plan.pdf", pdf_bytes, "application/pdf"))],
            headers=headers,
        )
        assert upload_resp.status_code == 201
        doc_info = upload_resp.json()[0]
        doc_id = doc_info["id"]

        # Fetch stored key from DB
        db_doc = db_session.get(Document, doc_id)
        assert db_doc is not None
        stored_key = db_doc.stored_filename
        assert s3_storage.exists(stored_key) is True

        # 2. Download via API
        download_resp = client.get(f"/document/{doc_id}", headers=headers)
        assert download_resp.status_code == 200
        assert download_resp.content == pdf_bytes

        # 3. Delete via API
        del_resp = client.delete(f"/document/{doc_id}", headers=headers)
        assert del_resp.status_code == 204
        assert s3_storage.exists(stored_key) is False

    finally:
        app.dependency_overrides.pop(original_get_storage, None)
