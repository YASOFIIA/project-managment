import io
import re
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from lambdas.size_limit.handler import S3_KEY_PATTERN
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.domain.errors import DomainError
from app.models.document import Document
from app.models.project import ProjectRole
from app.storage import get_storage
from tests.factories import create_project, create_project_member, create_user


def test_upload_single_document_by_owner_success(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Verify owner can upload a valid PDF document to their project."""
    owner = create_user(db_session, login="doc_owner")
    project = create_project(db_session, name="Document Project")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = b"%PDF-1.4 Sample research paper binary content"
    files = [("files", ("research_paper.pdf", io.BytesIO(pdf_content), "application/pdf"))]

    response = client.post(f"/project/{project.id}/documents", files=files, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    doc = data[0]
    assert doc["filename"] == "research_paper.pdf"
    assert doc["file_size_bytes"] == len(pdf_content)
    assert doc["content_type"] == "application/pdf"
    assert doc["project_id"] == project.id
    assert "id" in doc
    assert "created_at" in doc

    # Verify project total_size_bytes updated in DB
    db_session.refresh(project)
    assert project.total_size_bytes == len(pdf_content)


def test_upload_multiple_documents_by_participant_success(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify project participant can upload a batch of multiple files (PDF and DOCX)."""
    owner = create_user(db_session, login="owner_multi")
    participant = create_user(db_session, login="part_multi")
    project = create_project(db_session, name="Multi Doc Project")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    token = create_access_token(user_id=participant.id, login=participant.login)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = b"%PDF-1.7 Architecture diagram"
    docx_bytes = b"PK\x03\x04\x14\x00 Project requirements"
    docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    files = [
        ("files", ("diagram.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
        ("files", ("spec.docx", io.BytesIO(docx_bytes), docx_mime)),
    ]

    response = client.post(f"/project/{project.id}/documents", files=files, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    filenames = [d["filename"] for d in data]
    assert "diagram.pdf" in filenames
    assert "spec.docx" in filenames

    # Verify total size accumulates
    db_session.refresh(project)
    assert project.total_size_bytes == len(pdf_bytes) + len(docx_bytes)


def test_list_project_documents_by_owner_and_participant(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify listing documents returns attached document metadata in chronological order."""
    owner = create_user(db_session, login="owner_lister")
    participant = create_user(db_session, login="part_lister")
    project = create_project(db_session, name="Listing Project")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    part_token = create_access_token(user_id=participant.id, login=participant.login)

    # Initially empty
    resp_empty = client.get(
        f"/project/{project.id}/documents",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_empty.status_code == 200
    assert resp_empty.json() == []

    # Upload 1 file
    pdf_bytes = b"%PDF-1.4 Test file"
    client.post(
        f"/project/{project.id}/documents",
        files=[("files", ("file1.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # Participant lists documents
    resp_part = client.get(
        f"/project/{project.id}/documents",
        headers={"Authorization": f"Bearer {part_token}"},
    )
    assert resp_part.status_code == 200
    docs = resp_part.json()
    assert len(docs) == 1
    assert docs[0]["filename"] == "file1.pdf"


def test_upload_and_list_documents_non_member_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify non-members receive 404 for upload and list (Information Hiding)."""
    owner = create_user(db_session, login="owner_secret")
    stranger = create_user(db_session, login="stranger_doc")
    project = create_project(db_session, name="Secret Doc Project")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    token = create_access_token(user_id=stranger.id, login=stranger.login)
    headers = {"Authorization": f"Bearer {token}"}

    # Upload
    pdf_bytes = b"%PDF-1.4 Hacker attempt"
    upload_res = client.post(
        f"/project/{project.id}/documents",
        files=[("files", ("attack.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
        headers=headers,
    )
    assert upload_res.status_code == 404

    # List
    list_res = client.get(f"/project/{project.id}/documents", headers=headers)
    assert list_res.status_code == 404


def test_upload_and_list_unauthenticated_returns_401(client: TestClient) -> None:
    """Verify unauthenticated requests return 401 Unauthorized."""
    assert client.get("/project/1/documents").status_code == 401
    assert client.post("/project/1/documents").status_code == 401


def test_upload_validation_errors(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify validation errors (bad extension, spoofed signature, empty file) return 400."""
    owner = create_user(db_session, login="owner_val_err")
    project = create_project(db_session, name="Validation Test Project")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {token}"}

    # Disallowed extension (.exe)
    res_exe = client.post(
        f"/project/{project.id}/documents",
        files=[("files", ("virus.exe", io.BytesIO(b"MZ12345"), "application/x-msdownload"))],
        headers=headers,
    )
    assert res_exe.status_code == 400
    assert "not allowed" in res_exe.json()["detail"]

    # Spoofed signature (name .pdf, content is not PDF)
    res_fake = client.post(
        f"/project/{project.id}/documents",
        files=[("files", ("fake.pdf", io.BytesIO(b"not a valid pdf header"), "application/pdf"))],
        headers=headers,
    )
    assert res_fake.status_code == 400
    assert "signature does not match" in res_fake.json()["detail"]

    # Empty file
    res_empty = client.post(
        f"/project/{project.id}/documents",
        files=[("files", ("empty.pdf", io.BytesIO(b""), "application/pdf"))],
        headers=headers,
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"]


def test_upload_exceeding_project_size_limit_returns_413(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    """Verify uploading files that exceed project limit returns 413 Content Too Large."""
    owner = create_user(db_session, login="owner_quota")
    project = create_project(db_session, name="Quota Project")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    # Set project size already near limit
    project.total_size_bytes = 52_428_750  # 50 bytes below 50 MB
    db_session.commit()

    token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {token}"}

    # Upload a 100-byte PDF
    pdf_bytes = b"%PDF-" + b"0" * 95
    response = client.post(
        f"/project/{project.id}/documents",
        files=[("files", ("exceed.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
        headers=headers,
    )
    assert response.status_code == 413
    assert "limit" in response.json()["detail"]


def test_concurrent_uploads_cannot_bypass_project_size_limit() -> None:
    """Verify that row locking with with_for_update prevents race conditions."""
    import concurrent.futures
    import threading
    import uuid

    from fastapi import HTTPException, UploadFile
    from sqlalchemy import create_engine
    from starlette.datastructures import Headers

    from app.core.config import get_settings
    from app.models.document import Document
    from app.models.project import Project
    from app.models.user import User
    from app.services.documents import upload_documents
    from app.storage import get_storage

    settings = get_settings()
    engine = create_engine(settings.test_database_url, pool_pre_ping=True)

    with Session(engine) as init_session:
        user = create_user(init_session, login=f"race_user_{uuid.uuid4().hex[:6]}")
        project = create_project(
            init_session, name="Race Project", total_size_bytes=52_428_700
        )  # 100 bytes left
        create_project_member(
            init_session, project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
        )
        init_session.commit()
        project_id = project.id
        user_id = user.id

    barrier = threading.Barrier(2)
    results: list[tuple[str, Any]] = []

    def attempt_upload(worker_id: int) -> None:
        file_bytes = b"%PDF-" + b"A" * 70  # 75 bytes: 75 <= 100, but 75 + 75 = 150 > 100
        file_obj = io.BytesIO(file_bytes)
        upload_file = UploadFile(
            file=file_obj,
            filename=f"race_{worker_id}.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )
        storage = get_storage()
        with Session(engine) as session:
            try:
                barrier.wait(timeout=5)
                docs = upload_documents(
                    db=session,
                    storage=storage,
                    project_id=project_id,
                    user_id=user_id,
                    files=[upload_file],
                )
                results.append(("success", docs))
            except (HTTPException, DomainError) as exc:
                results.append(("error", exc.status_code))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_upload, 1)
        f2 = executor.submit(attempt_upload, 2)
        f1.result()
        f2.result()

    statuses = [r[0] for r in results]
    assert "success" in statuses
    assert "error" in statuses

    error_code = [r[1] for r in results if r[0] == "error"][0]
    assert error_code == 413

    # Verify database state in a fresh session
    with Session(engine) as verify_session:
        proj = verify_session.get(Project, project_id)
        assert proj is not None
        assert proj.total_size_bytes <= settings.project_size_limit_bytes

        # Only exactly 1 document was recorded
        docs_count = (
            verify_session.query(Document).filter(Document.project_id == project_id).count()
        )
        assert docs_count == 1

        # Clean up test rows
        verify_session.delete(proj)
        usr = verify_session.get(User, user_id)
        if usr:
            verify_session.delete(usr)
        verify_session.commit()

    engine.dispose()


def test_upload_key_does_not_leak_client_filename_and_matches_lambda_regex(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify stored key uses UUID filename, does not leak client name, and matches Lambda regex."""
    owner = create_user(db_session, login="secure_key_owner")
    project = create_project(db_session, name="Key Security Project")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {token}"}

    client_filename = "classified_internal_secret_roadmap_2026.pdf"
    pdf_content = b"%PDF-1.4 Secret Roadmap Content"
    files = [("files", (client_filename, io.BytesIO(pdf_content), "application/pdf"))]

    resp = client.post(f"/project/{project.id}/documents", files=files, headers=headers)
    assert resp.status_code == 201
    doc_id = resp.json()[0]["id"]

    # Verify original name in DB
    doc_db = db_session.get(Document, doc_id)
    assert doc_db is not None
    assert doc_db.filename == client_filename

    # Stored key must NOT contain the client's original filename
    assert client_filename not in doc_db.stored_filename
    assert "classified" not in doc_db.stored_filename
    assert "roadmap" not in doc_db.stored_filename

    # Stored key must match the Lambda key regex: projects/<project_id>/<document_id>/<stored_name>
    lambda_regex = r"^projects/\d+/\d+/.+"
    assert re.match(lambda_regex, doc_db.stored_filename) is not None

    # Stored key must match S3_KEY_PATTERN exactly
    match = S3_KEY_PATTERN.match(doc_db.stored_filename)
    assert match is not None
    assert int(match.group("project_id")) == project.id
    assert int(match.group("document_id")) == doc_id
    stored_name = match.group("filename")
    assert re.match(r"^[0-9a-f]{32}\.pdf$", stored_name) is not None

    # Storage backend confirms existence under this key
    storage = get_storage()
    assert storage.exists(doc_db.stored_filename) is True
