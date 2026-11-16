# Integration tests for internal Lambda callback API
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.domain.roles import ProjectRole
from app.models.document import Document
from tests.factories import create_document, create_project, create_project_member, create_user


def test_lambda_callback_success_accepted(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_settings()
    user = create_user(db_session)
    project = create_project(db_session, total_size_bytes=1000)
    create_project_member(
        db_session, project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
    )
    doc = create_document(db_session, project_id=project.id, file_size_bytes=5000)

    headers = {"X-Lambda-Secret": settings.lambda_callback_secret}
    payload = {
        "project_id": project.id,
        "document_id": doc.id,
        "filename": doc.filename,
        "status": "accepted",
        "total_size_bytes": 6000,
        "limit_bytes": settings.project_size_limit_bytes,
    }

    response = client.post("/internal/lambda/quota-alert", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["project_id"] == project.id
    assert data["document_id"] == doc.id
    assert data["total_size_bytes"] == 6000

    # Verify project total_size_bytes in DB was updated
    db_session.refresh(project)
    assert project.total_size_bytes == 6000

    # Document must still exist in DB
    refreshed_doc = db_session.get(Document, doc.id)
    assert refreshed_doc is not None


def test_lambda_callback_success_rejected_purges_document(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_settings()
    user = create_user(db_session)
    project = create_project(db_session, total_size_bytes=50_000_000)
    create_project_member(
        db_session, project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
    )
    doc = create_document(db_session, project_id=project.id, file_size_bytes=10_000_000)

    headers = {"X-Lambda-Secret": settings.lambda_callback_secret}
    payload = {
        "project_id": project.id,
        "document_id": doc.id,
        "filename": doc.filename,
        "status": "rejected",
        "total_size_bytes": 50_000_000,
        "limit_bytes": settings.project_size_limit_bytes,
    }

    response = client.post("/internal/lambda/quota-alert", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert "purged" in data["message"]

    # Verify document was deleted from DB
    purged_doc = db_session.get(Document, doc.id)
    assert purged_doc is None

    # Project total_size_bytes is synchronized
    db_session.refresh(project)
    assert project.total_size_bytes == 50_000_000


def test_lambda_callback_missing_secret_returns_403(
    client: TestClient,
    db_session: Session,
) -> None:
    project = create_project(db_session)
    doc = create_document(db_session, project_id=project.id)

    payload = {
        "project_id": project.id,
        "document_id": doc.id,
        "filename": doc.filename,
        "status": "accepted",
        "total_size_bytes": 1000,
        "limit_bytes": 50_000_000,
    }

    response = client.post("/internal/lambda/quota-alert", json=payload)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


def test_lambda_callback_invalid_secret_returns_403(
    client: TestClient,
    db_session: Session,
) -> None:
    project = create_project(db_session)
    doc = create_document(db_session, project_id=project.id)

    headers = {"X-Lambda-Secret": "wrong-secret-token"}
    payload = {
        "project_id": project.id,
        "document_id": doc.id,
        "filename": doc.filename,
        "status": "accepted",
        "total_size_bytes": 1000,
        "limit_bytes": 50_000_000,
    }

    response = client.post("/internal/lambda/quota-alert", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


def test_lambda_callback_with_user_jwt_without_secret_returns_403(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_user(db_session)
    project = create_project(db_session)
    doc = create_document(db_session, project_id=project.id)
    token = create_access_token(user_id=user.id, login=user.login)

    # Calling with JWT Bearer instead of X-Lambda-Secret must be rejected
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "project_id": project.id,
        "document_id": doc.id,
        "filename": doc.filename,
        "status": "accepted",
        "total_size_bytes": 1000,
        "limit_bytes": 50_000_000,
    }

    response = client.post("/internal/lambda/quota-alert", json=payload, headers=headers)
    assert response.status_code == 403


def test_lambda_callback_nonexistent_project_returns_404(
    client: TestClient,
) -> None:
    settings = get_settings()
    headers = {"X-Lambda-Secret": settings.lambda_callback_secret}
    payload = {
        "project_id": 999999,
        "document_id": 1,
        "filename": "file.pdf",
        "status": "accepted",
        "total_size_bytes": 1000,
        "limit_bytes": 50_000_000,
    }

    response = client.post("/internal/lambda/quota-alert", json=payload, headers=headers)
    assert response.status_code == 404
    assert "Project 999999 not found" in response.json()["detail"]


def test_lambda_callback_validation_error_returns_422(
    client: TestClient,
) -> None:
    settings = get_settings()
    headers = {"X-Lambda-Secret": settings.lambda_callback_secret}

    # Invalid status value
    payload = {
        "project_id": 1,
        "document_id": 1,
        "filename": "file.pdf",
        "status": "invalid_status",
        "total_size_bytes": 1000,
        "limit_bytes": 50_000_000,
    }

    response = client.post("/internal/lambda/quota-alert", json=payload, headers=headers)
    assert response.status_code == 422


# Check an invalid or missing Lambda secret returns 403 without accessing DB/UoW
def test_lambda_callback_invalid_or_missing_secret_does_not_touch_db(
    client: TestClient,
) -> None:
    from unittest.mock import patch

    payload = {
        "project_id": 1,
        "document_id": 1,
        "filename": "file.pdf",
        "status": "accepted",
        "total_size_bytes": 1000,
        "limit_bytes": 50_000_000,
    }

    # 1. Missing secret header
    with patch("app.api.deps.get_db") as mock_get_db:
        res1 = client.post("/internal/lambda/quota-alert", json=payload)
        assert res1.status_code == 403
        mock_get_db.assert_not_called()

    # 2. Invalid secret header
    with patch("app.api.deps.get_db") as mock_get_db:
        res2 = client.post(
            "/internal/lambda/quota-alert",
            json=payload,
            headers={"X-Lambda-Secret": "wrong_secret"},
        )
        assert res2.status_code == 403
        mock_get_db.assert_not_called()
