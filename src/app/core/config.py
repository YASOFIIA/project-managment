from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Project Management Service"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database (PostgreSQL 16 with psycopg 3 driver)
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pm_db"
    test_database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pm_test_db"

    # Security & JWT (lifetime exactly 1 hour = 60 minutes)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # File Storage
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "./data/storage"

    # AWS / LocalStack Configuration
    aws_region: str = "eu-central-1"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_endpoint_url: str | None = "http://localhost:4566"
    s3_bucket_name: str = "pm-documents"

    # Lambda Integration & Limits
    lambda_callback_secret: str
    project_size_limit_bytes: int = 52428800  # 50 MB
    max_file_size_bytes: int = 52428800  # 50 MB


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton instance."""
    return Settings()
