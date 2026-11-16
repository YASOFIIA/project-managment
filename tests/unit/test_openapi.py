# OpenAPI schema generation tests
from app.main import create_app


# Check OpenAPI schema converts contentMediaType to format: binary for file uploads
def test_openapi_schema_replaces_content_media_type_with_format_binary() -> None:
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


# Check openapi schema is cached on the app instance
def test_openapi_schema_is_cached() -> None:
    app = create_app()
    schema_first = app.openapi()
    schema_second = app.openapi()
    assert schema_first is schema_second
