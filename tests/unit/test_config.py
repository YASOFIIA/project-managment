import os
from unittest.mock import patch

from app.core.config import Settings, get_settings


def test_get_settings_defaults() -> None:
    """Verify that default settings comply with project specifications."""
    settings = get_settings()
    assert settings.app_name == "Project Management Service"
    assert settings.jwt_access_token_expire_minutes == 60
    assert settings.storage_backend in ("local", "s3")
    assert settings.project_size_limit_bytes == 52428800


def test_settings_env_override() -> None:
    """Verify that environment variables override default settings."""
    with patch.dict(os.environ, {"ENVIRONMENT": "testing", "DEBUG": "true"}):
        test_settings = Settings()
        assert test_settings.environment == "testing"
        assert test_settings.debug is True
