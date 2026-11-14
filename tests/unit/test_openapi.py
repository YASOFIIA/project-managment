"""Tests for custom OpenAPI schema generation and Swagger UI compatibility."""

from app.main import create_app


def test_openapi_schema_replaces_content_media_type_with_format_binary() -> None:
    """Verify OpenAPI schema converts contentMediaType to format: binary for file uploads."""
    app = create_app()
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    upload_schema_key = next(k for k in schemas if k.startswith("Body_upload_files_"))
    upload_files_prop = schemas[upload_schema_key]["properties"]["files"]
    assert upload_files_prop["items"]["format"] == "binary"
    assert "contentMediaType" not in upload_files_prop["items"]

    update_schema_key = next(k for k in schemas if k.startswith("Body_update_file_"))
    update_file_prop = schemas[update_schema_key]["properties"]["file"]
    assert update_file_prop["format"] == "binary"
    assert "contentMediaType" not in update_file_prop


def test_openapi_schema_is_cached() -> None:
    """Verify openapi schema is cached on the app instance."""
    app = create_app()
    schema_first = app.openapi()
    schema_second = app.openapi()
    assert schema_first is schema_second
