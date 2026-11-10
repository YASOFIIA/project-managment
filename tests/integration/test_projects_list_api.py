from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.raw_queries import (
    get_user_projects_with_documents_orm,
    get_user_projects_with_documents_raw,
)
from app.models.project import ProjectRole
from tests.factories import (
    create_document,
    create_project,
    create_project_member,
    create_user,
)


def test_get_projects_empty_for_new_user(client: TestClient, db_session: Session) -> None:
    """Verify that a user without any project memberships receives an empty list."""
    user = create_user(db_session, login="lonely_user")
    token = create_access_token(user_id=user.id, login=user.login)

    response = client.get(
        "/projects",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_projects_returns_accessible_projects_with_nested_documents(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that GET /projects returns only accessible projects with their attached documents."""
    user_a = create_user(db_session, login="user_a")
    user_b = create_user(db_session, login="user_b")
    user_c = create_user(db_session, login="user_c")

    # Project 1: owned by user_a, has 2 documents
    proj1 = create_project(db_session, name="Project Alpha")
    create_project_member(db_session, proj1.id, user_a.id, role=ProjectRole.OWNER)
    doc1_a = create_document(db_session, proj1.id, filename="doc1.pdf")
    doc1_b = create_document(db_session, proj1.id, filename="doc2.pdf")

    # Project 2: owned by user_b, user_a is participant, has 1 document
    proj2 = create_project(db_session, name="Project Beta")
    create_project_member(db_session, proj2.id, user_b.id, role=ProjectRole.OWNER)
    create_project_member(db_session, proj2.id, user_a.id, role=ProjectRole.PARTICIPANT)
    doc2_a = create_document(db_session, proj2.id, filename="doc3.pdf")

    # Project 3: owned by user_c, user_a has NO access
    proj3 = create_project(db_session, name="Project Secret Gamma")
    create_project_member(db_session, proj3.id, user_c.id, role=ProjectRole.OWNER)
    create_document(db_session, proj3.id, filename="secret.pdf")

    db_session.flush()

    token_a = create_access_token(user_id=user_a.id, login=user_a.login)
    response = client.get(
        "/projects",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 200
    data = response.json()

    # User A must see exactly 2 projects (Alpha and Beta), not Gamma
    returned_ids = {p["id"] for p in data}
    assert returned_ids == {proj1.id, proj2.id}
    assert proj3.id not in returned_ids

    # Check documents under Project Alpha
    proj1_data = next(p for p in data if p["id"] == proj1.id)
    doc_ids_1 = {d["id"] for d in proj1_data["documents"]}
    assert doc_ids_1 == {doc1_a.id, doc1_b.id}

    # Check documents under Project Beta
    proj2_data = next(p for p in data if p["id"] == proj2.id)
    doc_ids_2 = {d["id"] for d in proj2_data["documents"]}
    assert doc_ids_2 == {doc2_a.id}


def test_raw_sql_and_orm_produce_identical_results(db_session: Session) -> None:
    """Verify that get_user_projects_with_documents_raw matches ORM query results."""
    user = create_user(db_session, login="query_comparator")
    proj = create_project(db_session, name="Comparison Project")
    create_project_member(db_session, proj.id, user.id, role=ProjectRole.OWNER)
    doc1 = create_document(db_session, proj.id, filename="doc1.docx")
    doc2 = create_document(db_session, proj.id, filename="doc2.docx")

    db_session.flush()

    raw_results = get_user_projects_with_documents_raw(db_session, user.id)
    orm_results = get_user_projects_with_documents_orm(db_session, user.id)

    assert len(raw_results) == len(orm_results) == 1

    raw_proj = raw_results[0]
    orm_proj = orm_results[0]

    assert raw_proj["id"] == orm_proj.id
    assert raw_proj["name"] == orm_proj.name
    assert raw_proj["total_size_bytes"] == orm_proj.total_size_bytes

    raw_doc_ids = {d["id"] for d in raw_proj["documents"]}
    orm_doc_ids = {d.id for d in orm_proj.documents}
    assert raw_doc_ids == orm_doc_ids == {doc1.id, doc2.id}


def test_get_projects_unauthenticated_returns_401(client: TestClient) -> None:
    """Verify that GET /projects requires valid authentication."""
    response = client.get("/projects")
    assert response.status_code == 401
