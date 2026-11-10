import io
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.document import Document
from app.models.project import ProjectRole
from app.storage import get_storage
from tests.factories import create_document, create_project, create_project_member, create_user


def test_download_document_success(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    """Verify owner and participant can download a document's binary payload."""
    owner = create_user(db_session, login="owner_downloader")
    participant = create_user(db_session, login="part_downloader")
    project = create_project(db_session, name="Download Project")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    storage = get_storage()
    pdf_content = b"%PDF-1.4 Important Blueprint Specifications"
    stored_name = "test_blueprint.pdf"
    storage.save(stored_name, pdf_content)

    doc = create_document(
        db_session,
        project_id=project.id,
        filename="blueprint.pdf",
        stored_filename=stored_name,
        file_size_bytes=len(pdf_content),
        content_type="application/pdf",
    )

    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    part_token = create_access_token(user_id=participant.id, login=participant.login)

    # 1. Download by owner
    resp_owner = client.get(
        f"/document/{doc.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_owner.status_code == 200
    assert resp_owner.content == pdf_content
    assert resp_owner.headers["content-type"] == "application/pdf"
    assert "blueprint.pdf" in resp_owner.headers["content-disposition"]

    # 2. Download by participant
    resp_part = client.get(
        f"/document/{doc.id}",
        headers={"Authorization": f"Bearer {part_token}"},
    )
    assert resp_part.status_code == 200
    assert resp_part.content == pdf_content


def test_replace_document_success(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify document replacement updates metadata, storage files, and project size."""
    owner = create_user(db_session, login="owner_replacer")
    participant = create_user(db_session, login="part_replacer")
    project = create_project(db_session, name="Replace Project")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    storage = get_storage()
    old_content = b"%PDF-1.4 Initial Version"
    old_key = "initial_doc.pdf"
    storage.save(old_key, old_content)

    doc = create_document(
        db_session,
        project_id=project.id,
        filename="draft.pdf",
        stored_filename=old_key,
        file_size_bytes=len(old_content),
        content_type="application/pdf",
    )
    project.total_size_bytes = len(old_content)
    db_session.commit()

    part_token = create_access_token(user_id=participant.id, login=participant.login)
    headers = {"Authorization": f"Bearer {part_token}"}

    # Replace with a new docx file
    docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    new_content = b"PK\x03\x04\x14\x00 Updated Revised Manuscript with much more content"
    files = {"file": ("final_v2.docx", io.BytesIO(new_content), docx_mime)}

    response = client.put(f"/document/{doc.id}", files=files, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert data["filename"] == "final_v2.docx"
    assert data["file_size_bytes"] == len(new_content)
    assert data["content_type"] == docx_mime

    # Verify old file removed and new file present in storage
    assert storage.exists(old_key) is False
    db_session.refresh(doc)
    assert storage.exists(doc.stored_filename) is True

    # Verify project total_size_bytes accurately updated
    db_session.refresh(project)
    assert project.total_size_bytes == len(new_content)


def test_delete_document_success(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify document deletion removes row from DB, deletes file, and updates size."""
    owner = create_user(db_session, login="owner_deleter_doc")
    participant = create_user(db_session, login="part_deleter_doc")
    project = create_project(db_session, name="Delete Doc Project")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    storage = get_storage()
    content = b"%PDF-1.4 Content to be deleted"
    key = "doomed.pdf"
    storage.save(key, content)

    doc = create_document(
        db_session,
        project_id=project.id,
        filename="doomed.pdf",
        stored_filename=key,
        file_size_bytes=len(content),
    )
    project.total_size_bytes = len(content)
    db_session.commit()

    # Participant deletes document (per requirement: participant can delete documents)
    part_token = create_access_token(user_id=participant.id, login=participant.login)
    headers = {"Authorization": f"Bearer {part_token}"}

    response = client.delete(f"/document/{doc.id}", headers=headers)

    assert response.status_code == 204
    assert response.text == ""

    # Verify gone from DB and storage
    assert db_session.get(Document, doc.id) is None
    assert storage.exists(key) is False

    # Verify project total size reduced
    db_session.refresh(project)
    assert project.total_size_bytes == 0


def test_document_operations_non_member_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify non-members receive 404 for download, replace, and delete."""
    owner = create_user(db_session, login="owner_hide_doc")
    stranger = create_user(db_session, login="stranger_hide_doc")
    project = create_project(db_session, name="Private Project")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    doc = create_document(db_session, project_id=project.id, filename="confidential.pdf")

    stranger_token = create_access_token(user_id=stranger.id, login=stranger.login)
    headers = {"Authorization": f"Bearer {stranger_token}"}

    # Download
    assert client.get(f"/document/{doc.id}", headers=headers).status_code == 404

    # Replace
    files = {"file": ("new.pdf", io.BytesIO(b"%PDF-1.4 new"), "application/pdf")}
    assert client.put(f"/document/{doc.id}", files=files, headers=headers).status_code == 404

    # Delete
    assert client.delete(f"/document/{doc.id}", headers=headers).status_code == 404


def test_document_operations_nonexistent_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify operations on non-existent document ID return 404."""
    user = create_user(db_session, login="user_missing_doc")
    token = create_access_token(user_id=user.id, login=user.login)
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/document/99999", headers=headers).status_code == 404
    files = {"file": ("new.pdf", io.BytesIO(b"%PDF-1.4 new"), "application/pdf")}
    assert client.put("/document/99999", files=files, headers=headers).status_code == 404
    assert client.delete("/document/99999", headers=headers).status_code == 404


def test_document_operations_unauthenticated_returns_401(client: TestClient) -> None:
    """Verify unauthenticated requests to document operations return 401."""
    assert client.get("/document/1").status_code == 401
    assert client.put("/document/1").status_code == 401
    assert client.delete("/document/1").status_code == 401


def test_replace_document_validation_errors(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify replacing document with invalid type or spoofed bytes returns 400."""
    owner = create_user(db_session, login="owner_bad_replace")
    project = create_project(db_session, name="Bad Replace Project")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    doc = create_document(db_session, project_id=project.id, filename="valid.pdf")

    token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {token}"}

    # Bad extension (.exe)
    bad_ext_files = {"file": ("malware.exe", io.BytesIO(b"MZ123"), "application/octet-stream")}
    res_ext = client.put(f"/document/{doc.id}", files=bad_ext_files, headers=headers)
    assert res_ext.status_code == 400
    assert "not allowed" in res_ext.json()["detail"]

    # Spoofed magic bytes
    bad_bytes_files = {"file": ("spoofed.pdf", io.BytesIO(b"not a pdf"), "application/pdf")}
    res_bytes = client.put(f"/document/{doc.id}", files=bad_bytes_files, headers=headers)
    assert res_bytes.status_code == 400
    assert "signature does not match" in res_bytes.json()["detail"]
