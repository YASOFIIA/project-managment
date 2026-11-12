import uuid
from dataclasses import dataclass
from pathlib import Path

from app.domain.errors import (
    EmptyFileError,
    EmptyFilenameError,
    FileTooLarge,
    InvalidFileExtension,
    InvalidFileSignature,
)

DEFAULT_MAX_FILE_SIZE_BYTES: int = 52_428_800  # 50 MB


@dataclass(frozen=True)
class FileTypeSpec:
    """Specification of an allowed file type."""

    extension: str
    mime_type: str
    magic_bytes: bytes


ALLOWED_FILE_TYPES: dict[str, FileTypeSpec] = {
    ".pdf": FileTypeSpec(
        extension=".pdf",
        mime_type="application/pdf",
        magic_bytes=b"%PDF-",
    ),
    ".docx": FileTypeSpec(
        extension=".docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        magic_bytes=b"PK\x03\x04",
    ),
    ".png": FileTypeSpec(
        extension=".png",
        mime_type="image/png",
        magic_bytes=b"\x89PNG\r\n\x1a\n",
    ),
    ".jpg": FileTypeSpec(
        extension=".jpg",
        mime_type="image/jpeg",
        magic_bytes=b"\xff\xd8\xff",
    ),
    ".jpeg": FileTypeSpec(
        extension=".jpeg",
        mime_type="image/jpeg",
        magic_bytes=b"\xff\xd8\xff",
    ),
}


def sanitize_filename(filename: str) -> str:
    """Clean and sanitize original user-supplied filename.

    Strips directory separators (both POSIX / and Windows \\) and whitespace.

    Raises:
        EmptyFilenameError: If filename is empty or contains no valid name characters.
    """
    normalized = filename.replace("\\", "/").rstrip("/")
    clean_name = normalized.split("/")[-1].strip()
    if not clean_name:
        raise EmptyFilenameError("Filename cannot be empty")
    return clean_name


def generate_safe_stored_filename(original_filename: str) -> str:
    """Generate a collision-free, secure storage key preserving the sanitized extension.

    Example: 'Quarterly Report.pdf' -> 'a1b2c3d4e5f6...pdf'
    """
    clean_name = sanitize_filename(original_filename)
    extension = Path(clean_name).suffix.lower()
    return f"{uuid.uuid4().hex}{extension}"


def validate_file_upload(
    filename: str,
    content: bytes,
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> tuple[str, str]:
    """Validate uploaded file metadata, size, extension, and binary signature.

    Args:
        filename: Declared file name from client.
        content: Binary content of the uploaded file.
        max_size_bytes: Maximum allowed byte size (defaults to 50 MB).

    Returns:
        tuple[clean_filename, content_type]

    Raises:
        ValidationError: If file is empty, extension is disallowed, or magic bytes mismatch.
        FileTooLarge: If file size exceeds the allowed limit.
    """
    clean_name = sanitize_filename(filename)

    # 1. Size validations
    if len(content) == 0:
        raise EmptyFileError("Uploaded file is empty (0 bytes)")

    if len(content) > max_size_bytes:
        raise FileTooLarge(
            f"File size ({len(content)} bytes) exceeds limit ({max_size_bytes} bytes)"
        )

    # 2. Extension validation
    extension = Path(clean_name).suffix.lower()
    if extension not in ALLOWED_FILE_TYPES:
        allowed_list = ", ".join(sorted(ALLOWED_FILE_TYPES.keys()))
        raise InvalidFileExtension(
            f"File extension '{extension}' is not allowed. Supported types: {allowed_list}"
        )

    type_spec = ALLOWED_FILE_TYPES[extension]

    # 3. Magic bytes (file signature) validation
    if not content.startswith(type_spec.magic_bytes):
        raise InvalidFileSignature(
            f"File content signature does not match declared type '{extension}' "
            f"({type_spec.mime_type})"
        )

    return clean_name, type_spec.mime_type
