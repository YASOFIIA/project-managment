from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from tests.factories import create_user


def test_get_current_user_valid_token(client: TestClient, db_session: Session) -> None:
    """Verify that a valid JWT token retrieves the authenticated user's profile."""
    user = create_user(db_session, login="auth_me_user")
    token = create_access_token(user_id=user.id, login=user.login)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["login"] == "auth_me_user"


def test_get_current_user_missing_header_returns_401(client: TestClient) -> None:
    """Verify that requests without an Authorization header return 401 Unauthorized."""
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert "credentials were not provided" in response.json()["detail"]
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_current_user_invalid_scheme_returns_401(client: TestClient) -> None:
    """Verify that non-Bearer auth schemes return 401 Unauthorized."""
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401


def test_get_current_user_expired_token_returns_401(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that an expired JWT token returns 401 Unauthorized."""
    user = create_user(db_session, login="expired_token_user")
    token = create_access_token(
        user_id=user.id,
        login=user.login,
        expires_delta=timedelta(seconds=-1),
    )

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]


def test_get_current_user_invalid_signature_returns_401(client: TestClient) -> None:
    """Verify that a token with an invalid signature returns 401 Unauthorized."""
    headers = {"Authorization": "Bearer invalid.token.payload"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401


def test_get_current_user_nonexistent_user_returns_401(client: TestClient) -> None:
    """Verify that a valid token pointing to a non-existent user returns 401 Unauthorized."""
    # Issue a token for user ID 999999 which does not exist in the DB
    token = create_access_token(user_id=999999, login="ghost_user")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert "User not found" in response.json()["detail"]


def test_get_current_user_non_numeric_sub_returns_401(client: TestClient) -> None:
    """Verify that a validly signed token with a non-numeric sub returns 401 Unauthorized."""
    from datetime import UTC, datetime

    import jwt

    from app.core.config import get_settings

    settings = get_settings()
    payload = {
        "sub": "not_a_number",
        "login": "test_user",
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert "Invalid token payload" in response.json()["detail"]
