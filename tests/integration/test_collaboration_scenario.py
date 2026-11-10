from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.project import Project
from app.models.user import User
from app.storage import get_storage


def test_full_collaboration_lifecycle_scenario(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify complete end-to-end multi-user collaboration workflow (T5.2):

    1. Register User A (Alice) and User B (Bob).
    2. Authenticate User A and User B via /login to obtain JWT tokens.
    3. User A creates a project; User B cannot see it (information hiding).
    4. User A uploads a document; project total size updates atomically.
    5. User A invites User B to the project; User B receives participant role.
    6. User B lists projects, sees the project and its attached document.
    7. User B downloads the document binary content.
    8. User B replaces the document with a revised version; storage and size update.
    9. User B updates project metadata (name, description).
    10. User B attempts to invite a third user -> 403 Forbidden.
    11. User B attempts to delete the project -> 403 Forbidden.
    12. User A deletes the project -> 204 No Content.
    13. Database rows (project, members, documents) are cascaded and removed.
    14. Physical files in StorageBackend are completely cleaned up.
    15. Both users receive 404 Not Found on subsequent access.
    """
    storage = get_storage()

    # --- Step 1: Register User A and User B ---
    reg_a = client.post(
        "/auth",
        json={"login": "alice", "password": "password123", "repeat_password": "password123"},
    )
    assert reg_a.status_code == 201
    user_a_id = reg_a.json()["id"]

    reg_b = client.post(
        "/auth",
        json={"login": "bob", "password": "password123", "repeat_password": "password123"},
    )
    assert reg_b.status_code == 201
    user_b_id = reg_b.json()["id"]

    # --- Step 2: Login User A and User B ---
    login_a = client.post("/login", json={"login": "alice", "password": "password123"})
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    login_b = client.post("/login", json={"login": "bob", "password": "password123"})
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # --- Step 3: User A creates project ---
    create_proj_resp = client.post(
        "/projects",
        json={
            "name": "Project Apollo",
            "description": "Exploration and science initiative",
        },
        headers=headers_a,
    )
    assert create_proj_resp.status_code == 201
    project_id = create_proj_resp.json()["id"]
    assert create_proj_resp.json()["total_size_bytes"] == 0

    # User B cannot see the project yet
    b_projects_initial = client.get("/projects", headers=headers_b)
    assert b_projects_initial.status_code == 200
    assert len(b_projects_initial.json()) == 0

    b_direct_info = client.get(f"/project/{project_id}/info", headers=headers_b)
    assert b_direct_info.status_code == 404

    # --- Step 4: User A uploads a document ---
    initial_pdf_bytes = b"%PDF-1.4 Initial Apollo Mission Flight Plan"
    upload_resp = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("flight_plan.pdf", initial_pdf_bytes, "application/pdf"))],
        headers=headers_a,
    )
    assert upload_resp.status_code == 201
    uploaded_docs = upload_resp.json()
    assert len(uploaded_docs) == 1
    doc_id = uploaded_docs[0]["id"]
    assert uploaded_docs[0]["file_size_bytes"] == len(initial_pdf_bytes)

    # Stored filename is internal to storage/database, not exposed in public DocumentResponse
    db_doc_initial = db_session.get(Document, doc_id)
    assert db_doc_initial is not None
    doc_stored_initial = db_doc_initial.stored_filename
    assert storage.exists(doc_stored_initial) is True

    # Check project total size updated for Alice
    proj_info_a = client.get(f"/project/{project_id}/info", headers=headers_a)
    assert proj_info_a.status_code == 200
    assert proj_info_a.json()["total_size_bytes"] == len(initial_pdf_bytes)

    # --- Step 5: User A invites User B ---
    invite_resp = client.post(
        f"/project/{project_id}/invite?user=bob",
        headers=headers_a,
    )
    assert invite_resp.status_code == 200
    invite_data = invite_resp.json()
    assert invite_data["project_id"] == project_id
    assert invite_data["user_id"] == user_b_id
    assert invite_data["role"] == "participant"

    # --- Step 6: User B lists projects and sees Apollo + documents ---
    b_projects = client.get("/projects", headers=headers_b)
    assert b_projects.status_code == 200
    b_project_list = b_projects.json()
    assert len(b_project_list) == 1
    assert b_project_list[0]["id"] == project_id
    assert b_project_list[0]["name"] == "Project Apollo"
    assert len(b_project_list[0]["documents"]) == 1
    assert b_project_list[0]["documents"][0]["id"] == doc_id
    assert b_project_list[0]["documents"][0]["filename"] == "flight_plan.pdf"

    # --- Step 7: User B downloads the document ---
    download_resp = client.get(f"/document/{doc_id}", headers=headers_b)
    assert download_resp.status_code == 200
    assert download_resp.content == initial_pdf_bytes
    assert download_resp.headers["content-type"] == "application/pdf"
    assert "flight_plan.pdf" in download_resp.headers["content-disposition"]

    # --- Step 8: User B replaces the document with a revised version ---
    revised_pdf_bytes = b"%PDF-1.4 Revision 2 with Lunar Orbit Coordinates & Trajectory"
    replace_resp = client.put(
        f"/document/{doc_id}",
        files={"file": ("flight_plan_v2.pdf", revised_pdf_bytes, "application/pdf")},
        headers=headers_b,
    )
    assert replace_resp.status_code == 200
    replace_data = replace_resp.json()
    assert replace_data["id"] == doc_id
    assert replace_data["filename"] == "flight_plan_v2.pdf"
    assert replace_data["file_size_bytes"] == len(revised_pdf_bytes)

    # Fetch updated stored_filename from DB
    db_session.expire_all()
    db_doc_revised = db_session.get(Document, doc_id)
    assert db_doc_revised is not None
    doc_stored_revised = db_doc_revised.stored_filename

    # Storage verifies old file deleted, new file saved
    assert storage.exists(doc_stored_initial) is False
    assert storage.exists(doc_stored_revised) is True

    # User B downloads revised version
    download_v2 = client.get(f"/document/{doc_id}", headers=headers_b)
    assert download_v2.status_code == 200
    assert download_v2.content == revised_pdf_bytes

    # Project size reflects the new size
    proj_info_b = client.get(f"/project/{project_id}/info", headers=headers_b)
    assert proj_info_b.status_code == 200
    assert proj_info_b.json()["total_size_bytes"] == len(revised_pdf_bytes)

    # --- Step 9: User B updates project metadata ---
    update_resp = client.put(
        f"/project/{project_id}/info",
        json={
            "name": "Project Apollo - Lunar Expedition",
            "description": "Updated flight objectives by Bob",
        },
        headers=headers_b,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Project Apollo - Lunar Expedition"
    assert update_resp.json()["description"] == "Updated flight objectives by Bob"

    # --- Step 10: User B attempts to invite someone else -> 403 Forbidden ---
    charlie_reg = client.post(
        "/auth",
        json={"login": "charlie", "password": "password123", "repeat_password": "password123"},
    )
    assert charlie_reg.status_code == 201

    invite_by_b_resp = client.post(
        f"/project/{project_id}/invite?user=charlie",
        headers=headers_b,
    )
    assert invite_by_b_resp.status_code == 403

    # --- Step 11: User B attempts to delete project -> 403 Forbidden ---
    delete_by_b_resp = client.delete(f"/project/{project_id}", headers=headers_b)
    assert delete_by_b_resp.status_code == 403

    # Verify project and files still exist after unauthorized delete attempt
    assert storage.exists(doc_stored_revised) is True

    # --- Step 12: User A deletes project -> 204 No Content ---
    delete_by_a_resp = client.delete(f"/project/{project_id}", headers=headers_a)
    assert delete_by_a_resp.status_code == 204

    # --- Step 13: Database verification ---
    db_session.expire_all()
    assert db_session.get(Project, project_id) is None
    assert db_session.get(Document, doc_id) is None

    # Users themselves remain intact
    assert db_session.get(User, user_a_id) is not None
    assert db_session.get(User, user_b_id) is not None

    # --- Step 14: StorageBackend verification ---
    assert storage.exists(doc_stored_initial) is False
    assert storage.exists(doc_stored_revised) is False

    # --- Step 15: Subsequent access returns 404 ---
    assert client.get(f"/project/{project_id}/info", headers=headers_a).status_code == 404
    assert client.get(f"/project/{project_id}/info", headers=headers_b).status_code == 404
    assert client.get(f"/document/{doc_id}", headers=headers_a).status_code == 404
    assert client.get(f"/document/{doc_id}", headers=headers_b).status_code == 404
