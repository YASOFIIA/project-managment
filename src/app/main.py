from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Application factory for creating and configuring the FastAPI instance."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Register API routers
    application.include_router(auth_router)
    application.include_router(projects_router)

    @application.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        """Health check endpoint accessible without authentication."""
        return {
            "status": "ok",
            "environment": settings.environment,
            "version": settings.app_version,
        }

    return application


app = create_app()
