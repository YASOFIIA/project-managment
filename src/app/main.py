from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.internal import router as internal_router
from app.api.invitations import router as invitations_router
from app.api.projects import router as projects_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.middleware import RequestIDLoggingMiddleware


# Fix OpenAPI file upload schema for Swagger UI
def _fix_file_upload_schemas(node: Any) -> None:
    if isinstance(node, dict):
        if (
            node.get("type") == "string"
            and node.get("contentMediaType") == "application/octet-stream"
        ):
            del node["contentMediaType"]
            node["format"] = "binary"
        for value in list(node.values()):
            _fix_file_upload_schemas(value)
    elif isinstance(node, list):
        for item in node:
            _fix_file_upload_schemas(item)


# Create and configure FastAPI application
def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Register error handlers and middleware
    register_error_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestIDLoggingMiddleware)

    # Register API routers
    application.include_router(auth_router)
    application.include_router(projects_router)
    application.include_router(documents_router)
    application.include_router(internal_router)
    application.include_router(invitations_router)

    def custom_openapi() -> dict[str, Any]:
        if application.openapi_schema:
            return application.openapi_schema
        openapi_schema = get_openapi(
            title=application.title,
            version=application.version,
            openapi_version=application.openapi_version,
            description=application.description,
            routes=application.routes,
        )
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        _fix_file_upload_schemas(schemas)
        application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi  # type: ignore[method-assign]

    # Service health check
    @application.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "environment": settings.environment,
            "version": settings.app_version,
        }

    return application


app = create_app()
