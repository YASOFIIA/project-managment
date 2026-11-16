import uuid
from unittest.mock import MagicMock

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.errors import get_error_code_name, get_request_id, register_error_handlers
from app.core.logging import sanitize_query_string
from app.core.middleware import RequestIDLoggingMiddleware


# Check any request gets an X-Request-ID header in response
def test_response_includes_x_request_id_header(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    # Check it's a valid uuid
    uuid.UUID(request_id)


# Check a client-provided X-Request-ID is preserved in response header
def test_incoming_x_request_id_is_preserved(client: TestClient) -> None:
    custom_id = "client-trace-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


# Check unmatched routes return 404 in unified JSON format
def test_404_not_found_unified_error_format(client: TestClient) -> None:
    custom_id = "test-404-id"
    response = client.get("/nonexistent-endpoint", headers={"X-Request-ID": custom_id})
    assert response.status_code == 404
    assert response.headers.get("X-Request-ID") == custom_id

    data = response.json()
    assert data["status_code"] == 404
    assert data["error_code"] == "NOT_FOUND"
    assert data["request_id"] == custom_id
    assert "detail" in data


# Check unsupported HTTP methods return 405 in unified JSON format
def test_405_method_not_allowed_unified_error_format(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 405
    assert "X-Request-ID" in response.headers

    data = response.json()
    assert data["status_code"] == 405
    assert data["error_code"] == "METHOD_NOT_ALLOWED"
    assert data["detail"] == "Method Not Allowed"
    assert data["request_id"] == response.headers["X-Request-ID"]


# Check validation errors return 422 in unified JSON format with detail list
def test_422_validation_error_unified_error_format(client: TestClient) -> None:
    response = client.post("/auth", json={"login": "short"})
    assert response.status_code == 422

    data = response.json()
    assert data["status_code"] == 422
    assert data["error_code"] == "UNPROCESSABLE_ENTITY"
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0
    assert "request_id" in data


# Check unexpected exceptions return 500 without leaking stack traces
def test_500_unhandled_exception_unified_error_format() -> None:
    test_app = FastAPI()
    register_error_handlers(test_app)
    test_app.add_middleware(RequestIDLoggingMiddleware)

    router = APIRouter()

    @router.get("/cause-error")
    def cause_error() -> None:
        raise RuntimeError("Something catastrophically unexpected occurred")

    test_app.include_router(router)
    custom_client = TestClient(test_app, raise_server_exceptions=False)

    response = custom_client.get("/cause-error", headers={"X-Request-ID": "err-500-trace"})
    assert response.status_code == 500
    assert response.headers.get("X-Request-ID") == "err-500-trace"

    data = response.json()
    assert data["status_code"] == 500
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert data["detail"] == "Internal server error"
    assert data["request_id"] == "err-500-trace"


# Check sensitive query parameters are masked and non-sensitive remain untouched
def test_sanitize_query_string() -> None:
    raw_query = "user=alice&password=secret123&token=jwt_xyz&page=2"
    sanitized = sanitize_query_string(raw_query)

    assert "password=%2A%2A%2A%2A%2A%2A" in sanitized or "password=******" in sanitized
    assert "token=%2A%2A%2A%2A%2A%2A" in sanitized or "token=******" in sanitized
    assert "secret123" not in sanitized
    assert "jwt_xyz" not in sanitized
    assert "user=alice" in sanitized
    assert "page=2" in sanitized

    assert sanitize_query_string("") == ""


# Check known and unknown status codes map properly to error names
def test_get_error_code_name() -> None:
    assert get_error_code_name(404) == "NOT_FOUND"
    assert get_error_code_name(999) == "HTTP_999"


# Check request ID extraction fallback behaviors
def test_get_request_id_fallbacks() -> None:
    # 1. Fallback to header if state has no request_id
    req_header_only = MagicMock(spec=Request)
    req_header_only.state = MagicMock(spec=[])
    req_header_only.headers = {"X-Request-ID": "from-header-123"}
    assert get_request_id(req_header_only) == "from-header-123"

    # 2. Fallback to generating a uuid if state and headers are empty
    req_empty = MagicMock(spec=Request)
    req_empty.state = MagicMock(spec=[])
    req_empty.headers = {}
    gen_id = get_request_id(req_empty)
    uuid.UUID(gen_id)
