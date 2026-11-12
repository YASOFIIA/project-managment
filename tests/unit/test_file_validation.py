import pytest

from app.domain.errors import DomainError
from app.services.file_validation import (
    generate_safe_stored_filename,
    sanitize_filename,
    validate_file_upload,
)


def test_sanitize_filename() -> None:
    """Verify filename sanitization strips directories and whitespace."""
    assert sanitize_filename("document.pdf") == "document.pdf"
    assert sanitize_filename("  spaces.docx  ") == "spaces.docx"
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("C:\\Users\\admin\\file.png") == "file.png"

    with pytest.raises(DomainError) as exc_info:
        sanitize_filename("   ")
    assert exc_info.value.status_code == 400
    assert "cannot be empty" in exc_info.value.detail


def test_generate_safe_stored_filename() -> None:
    """Verify unique, collision-free UUID stored filename generation."""
    name1 = generate_safe_stored_filename("Annual Report 2026.pdf")
    name2 = generate_safe_stored_filename("Annual Report 2026.pdf")

    assert name1.endswith(".pdf")
    assert name2.endswith(".pdf")
    assert name1 != name2
    # 32 hex chars + 4 chars (.pdf) = 36 chars
    assert len(name1) == 36


def test_validate_valid_pdf_and_docx() -> None:
    """Verify successful validation of PDF and DOCX files."""
    # PDF
    pdf_bytes = b"%PDF-1.7 valid pdf sample content"
    clean_name, mime = validate_file_upload("report.pdf", pdf_bytes)
    assert clean_name == "report.pdf"
    assert mime == "application/pdf"

    # DOCX
    docx_bytes = b"PK\x03\x04\x14\x00 word document package"
    clean_name, mime = validate_file_upload("thesis.docx", docx_bytes)
    assert clean_name == "thesis.docx"
    assert mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_validate_valid_images() -> None:
    """Verify validation of allowed image formats (PNG, JPG, JPEG)."""
    # PNG
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    _, mime_png = validate_file_upload("diagram.png", png_bytes)
    assert mime_png == "image/png"

    # JPG / JPEG
    jpg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    _, mime_jpg = validate_file_upload("photo.jpg", jpg_bytes)
    assert mime_jpg == "image/jpeg"

    _, mime_jpeg = validate_file_upload("photo.jpeg", jpg_bytes)
    assert mime_jpeg == "image/jpeg"


def test_validate_empty_file_rejected() -> None:
    """Verify that empty file uploads return 400 Bad Request."""
    with pytest.raises(DomainError) as exc_info:
        validate_file_upload("empty.pdf", b"")
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail


def test_validate_file_size_exceeded_rejected() -> None:
    """Verify that files exceeding the maximum size limit return 413 Payload Too Large."""
    large_pdf = b"%PDF-" + b"0" * 100
    with pytest.raises(DomainError) as exc_info:
        validate_file_upload("large.pdf", large_pdf, max_size_bytes=50)
    assert exc_info.value.status_code == 413
    assert "exceeds limit" in exc_info.value.detail


def test_validate_disallowed_extension_rejected() -> None:
    """Verify that disallowed extensions return 400 Bad Request."""
    bad_extensions = ["malware.exe", "script.sh", "notes.txt", "archive.zip", "test.py"]
    for fname in bad_extensions:
        with pytest.raises(DomainError) as exc_info:
            validate_file_upload(fname, b"any dummy content")
        assert exc_info.value.status_code == 400
        assert "not allowed" in exc_info.value.detail


def test_validate_spoofed_magic_bytes_rejected() -> None:
    """Verify that files with mismatched magic bytes return 400 Bad Request."""
    # Declared as PDF, but actually plain text / executable
    fake_pdf = b"MZ executable content disguised as pdf"
    with pytest.raises(DomainError) as exc_info:
        validate_file_upload("malicious.pdf", fake_pdf)
    assert exc_info.value.status_code == 400
    assert "signature does not match" in exc_info.value.detail

    # Declared as DOCX, but actually PDF
    fake_docx = b"%PDF-1.5 disguised as docx"
    with pytest.raises(DomainError) as exc_info:
        validate_file_upload("fake.docx", fake_docx)
    assert exc_info.value.status_code == 400
    assert "signature does not match" in exc_info.value.detail


def test_read_upload_file_limited_success() -> None:
    """Verify that read_upload_file_limited reads content within limit."""
    import io

    from fastapi import UploadFile

    from app.services.documents import read_upload_file_limited

    file = UploadFile(file=io.BytesIO(b"Hello world"), filename="test.txt")
    data = read_upload_file_limited(file, max_bytes=100)
    assert data == b"Hello world"


def test_read_upload_file_limited_exceeding_stops_reading() -> None:
    """Verify that read_upload_file_limited aborts immediately when exceeding max_bytes."""
    from unittest.mock import MagicMock

    from fastapi import UploadFile

    from app.domain.errors import FileTooLarge
    from app.services.documents import read_upload_file_limited

    mock_stream = MagicMock()
    # 3 chunks of 64 KB
    mock_stream.read.side_effect = [b"A" * 65536, b"B" * 65536, b"C" * 65536]
    file = UploadFile(file=mock_stream, filename="large.bin")

    with pytest.raises(FileTooLarge) as exc_info:
        read_upload_file_limited(file, max_bytes=70000)

    assert exc_info.value.status_code == 413
    assert "exceeds maximum allowed size" in exc_info.value.detail
    # Must have stopped reading after the 2nd chunk, without reading the 3rd chunk
    assert mock_stream.read.call_count == 2
