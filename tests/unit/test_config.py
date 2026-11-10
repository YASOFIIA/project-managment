import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_get_settings_defaults() -> None:
    """Verify that default settings comply with project specifications."""
    settings = get_settings()
    assert settings.app_name == "Project Management Service"
    assert settings.jwt_access_token_expire_minutes == 60
    assert settings.storage_backend in ("local", "s3")
    assert settings.project_size_limit_bytes == 52428800
    assert settings.jwt_secret_key is not None
    assert settings.lambda_callback_secret is not None


def test_settings_env_override() -> None:
    """Verify that environment variables override default settings."""
    with patch.dict(os.environ, {"ENVIRONMENT": "testing", "DEBUG": "true"}):
        test_settings = Settings()
        assert test_settings.environment == "testing"
        assert test_settings.debug is True


def test_settings_missing_secrets_raises_validation_error() -> None:
    """Verify that Settings cannot be initialized without required secrets."""
    with patch.dict(os.environ, {}, clear=True), pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    errors = exc_info.value.errors()
    missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
    assert "jwt_secret_key" in missing_fields
    assert "lambda_callback_secret" in missing_fields
