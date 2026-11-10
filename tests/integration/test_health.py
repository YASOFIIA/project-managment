from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check_returns_ok() -> None:
    """Verify that GET /health responds with 200 OK and expected status payload."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data
    assert "version" in data
