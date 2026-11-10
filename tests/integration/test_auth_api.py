from fastapi.testclient import TestClient

from app.core.security import decode_access_token


def test_register_user_success(client: TestClient) -> None:
    """Verify that POST /auth successfully creates a new user and returns 201."""
    payload = {
        "login": "newuser",
        "password": "SecretPassword123!",
        "repeat_password": "SecretPassword123!",
    }

    response = client.post("/auth", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["login"] == "newuser"
    assert "id" in data
    assert "created_at" in data
    # Password must NEVER be returned in response
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_user_mismatched_passwords_returns_422(client: TestClient) -> None:
    """Verify that POST /auth returns 422 when password and repeat_password differ."""
    payload = {
        "login": "mismatch_user",
        "password": "Password123!",
        "repeat_password": "DifferentPassword123!",
    }

    response = client.post("/auth", json=payload)

    assert response.status_code == 422
    errors = response.json().get("detail", [])
    assert any("Passwords do not match" in str(err) for err in errors)


def test_register_duplicate_login_returns_409(client: TestClient) -> None:
    """Verify that POST /auth returns 409 Conflict if login is already registered."""
    payload = {
        "login": "duplicate_user",
        "password": "ValidPassword123!",
        "repeat_password": "ValidPassword123!",
    }

    resp1 = client.post("/auth", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/auth", json=payload)
    assert resp2.status_code == 409
    assert "already taken" in resp2.json()["detail"]


def test_login_success_returns_jwt_token(client: TestClient) -> None:
    """Verify that POST /login with valid credentials returns 200 and a decodable JWT."""
    # First register user
    register_payload = {
        "login": "login_success_user",
        "password": "CorrectPassword123!",
        "repeat_password": "CorrectPassword123!",
    }
    client.post("/auth", json=register_payload)

    # Login
    login_payload = {
        "login": "login_success_user",
        "password": "CorrectPassword123!",
    }
    response = client.post("/login", json=login_payload)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify that returned token is cryptographically valid
    payload = decode_access_token(data["access_token"])
    assert payload["login"] == "login_success_user"


def test_login_invalid_password_returns_401(client: TestClient) -> None:
    """Verify that POST /login with incorrect password returns 401 Unauthorized."""
    register_payload = {
        "login": "wrong_pw_user",
        "password": "RealPassword123!",
        "repeat_password": "RealPassword123!",
    }
    client.post("/auth", json=register_payload)

    login_payload = {
        "login": "wrong_pw_user",
        "password": "IncorrectPassword123!",
    }
    response = client.post("/login", json=login_payload)

    assert response.status_code == 401
    assert "Invalid login or password" in response.json()["detail"]


def test_login_nonexistent_user_returns_401(client: TestClient) -> None:
    """Verify that POST /login with non-existent username returns 401 Unauthorized."""
    login_payload = {
        "login": "ghost_user",
        "password": "AnyPassword123!",
    }
    response = client.post("/login", json=login_payload)

    assert response.status_code == 401
    assert "Invalid login or password" in response.json()["detail"]
