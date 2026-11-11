import http
import uuid

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, request_id_ctx

logger = get_logger("app.errors")


def get_request_id(request: Request) -> str:
    """Retrieve the correlation request ID from request state, contextvar, or fallback."""
    state_id = getattr(request.state, "request_id", None)
    if state_id:
        return str(state_id)
    ctx_id = request_id_ctx.get()
    if ctx_id and ctx_id != "no-request-id":
        return ctx_id
    header_id = request.headers.get("X-Request-ID")
    if header_id:
        return header_id.strip()
    return str(uuid.uuid4())


def get_error_code_name(status_code: int) -> str:
    """Map HTTP status code to an UPPERCASE descriptive error code."""
    try:
        return http.HTTPStatus(status_code).name
    except ValueError:
        return f"HTTP_{status_code}"


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Unified handler for all HTTPExceptions (including 404 route not found, 405, etc.)."""
    request_id = get_request_id(request)
    headers = dict(exc.headers) if exc.headers else {}
    headers["X-Request-ID"] = request_id

    error_code = get_error_code_name(exc.status_code)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": jsonable_encoder(exc.detail),
            "status_code": exc.status_code,
            "error_code": error_code,
            "request_id": request_id,
        },
        headers=headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Unified handler for RequestValidationError (422 Unprocessable Content)."""
    request_id = get_request_id(request)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "error_code": "UNPROCESSABLE_ENTITY",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


async def file_not_found_exception_handler(
    request: Request,
    exc: FileNotFoundError,
) -> JSONResponse:
    """Unified handler for missing storage files (404 Not Found)."""
    request_id = get_request_id(request)
    logger.warning("File not found on storage: %s", exc)

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": str(exc) or "Requested file not found in storage",
            "status_code": status.HTTP_404_NOT_FOUND,
            "error_code": "NOT_FOUND",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions (500 Internal Server Error)."""
    request_id = get_request_id(request)
    logger.exception("Unhandled server exception: %s", exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "error_code": "INTERNAL_SERVER_ERROR",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


def register_error_handlers(application: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI application."""
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(FileNotFoundError, file_not_found_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, unhandled_exception_handler)
