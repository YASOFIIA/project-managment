import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, request_id_ctx, sanitize_query_string

logger = get_logger("app.middleware")


class RequestIDLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that injects X-Request-ID and logs incoming requests and responses safely.

    - Preserves client-supplied X-Request-ID or generates a new UUIDv4.
    - Attaches X-Request-ID to both the request state, contextvars, and response headers.
    - Logs method, path, sanitized query parameters, status code, and latency in ms.
    - Prevents sensitive credentials or token values from appearing in logs.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_request_id = request.headers.get("X-Request-ID")
        request_id = incoming_request_id.strip() if incoming_request_id else str(uuid.uuid4())

        # Store in request state and contextvar
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)

        # Log request start with sanitized query parameters
        sanitized_query = sanitize_query_string(request.url.query)
        path_with_query = (
            f"{request.url.path}?{sanitized_query}" if sanitized_query else request.url.path
        )
        logger.info("--> %s %s", request.method, path_with_query)

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "<-- %s %s 500 Internal Server Error (%.2fms)",
                request.method,
                path_with_query,
                duration_ms,
            )
            request_id_ctx.reset(token)
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "<-- %s %s %d (%.2fms)",
            request.method,
            path_with_query,
            response.status_code,
            duration_ms,
        )

        request_id_ctx.reset(token)
        return response
