from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token


def test_full_auth_lifecycle_end_to_end(client: TestClient) -> None:
    """Verify the entire authentication lifecycle in an integrated end-to-end scenario:

    1. Register a new user (POST /auth -> 201).
    2. Attempt duplicate registration (POST /auth -> 409).
    3. Login with wrong password (POST /login -> 401).
    4. Login with correct password (POST /login -> 200, JWT issued).
    5. Access protected endpoint with valid JWT (GET /auth/me -> 200).
    6. Access protected endpoint with tampered JWT (GET /auth/me -> 401).
    7. Access protected endpoint with expired JWT (GET /auth/me -> 401).
    8. Access protected endpoint without JWT (GET /auth/me -> 401).
    """
    username = "e2e_student"
    password = "StrongPassword2026!"

    # 1. Register new user
    register_resp = client.post(
        "/auth",
        json={
            "login": username,
            "password": password,
            "repeat_password": password,
        },
    )
    assert register_resp.status_code == 201
    user_data = register_resp.json()
    assert user_data["login"] == username
    user_id = user_data["id"]

    # 2. Attempt duplicate registration -> 409 Conflict
    dup_resp = client.post(
        "/auth",
        json={
            "login": username,
            "password": password,
            "repeat_password": password,
        },
    )
    assert dup_resp.status_code == 409

    # 3. Attempt login with wrong password -> 401 Unauthorized
    bad_login_resp = client.post(
        "/login",
        json={
            "login": username,
            "password": "WrongPassword!",
        },
    )
    assert bad_login_resp.status_code == 401

    # 4. Login with correct password -> 200 OK with Bearer token
    login_resp = client.post(
        "/login",
        json={
            "login": username,
            "password": password,
        },
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert token_data["token_type"] == "bearer"
    access_token = token_data["access_token"]
    assert len(access_token) > 20

    # 5. Access protected endpoint with valid JWT -> 200 OK
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    profile_resp = client.get("/auth/me", headers=auth_headers)
    assert profile_resp.status_code == 200
    profile_data = profile_resp.json()
    assert profile_data["id"] == user_id
    assert profile_data["login"] == username

    # 6. Access protected endpoint with tampered JWT -> 401 Unauthorized
    tampered_headers = {"Authorization": f"Bearer {access_token[:-4]}abcd"}
    tampered_resp = client.get("/auth/me", headers=tampered_headers)
    assert tampered_resp.status_code == 401

    # 7. Access protected endpoint with expired JWT -> 401 Unauthorized
    expired_token = create_access_token(
        user_id=user_id,
        login=username,
        expires_delta=timedelta(seconds=-1),
    )
    expired_headers = {"Authorization": f"Bearer {expired_token}"}
    expired_resp = client.get("/auth/me", headers=expired_headers)
    assert expired_resp.status_code == 401
    assert "Token has expired" in expired_resp.json()["detail"]

    # 8. Access protected endpoint without JWT -> 401 Unauthorized
    no_token_resp = client.get("/auth/me")
    assert no_token_resp.status_code == 401
