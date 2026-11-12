"""Domain exception hierarchy for the Project Management domain."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain business errors."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
        self.detail = message


# 404 Not Found
class NotFoundError(DomainError):
    """Base class for resource not found errors (HTTP 404)."""

    status_code: int = 404


class ProjectNotFound(NotFoundError):
    """Project does not exist or user has no access (information hiding)."""


class DocumentNotFound(NotFoundError):
    """Document does not exist or user has no access (information hiding)."""


class UserNotFound(NotFoundError):
    """Target user (e.g. invitee) does not exist."""


class StorageFileNotFound(NotFoundError):
    """File record exists in database, but physical object is missing from storage."""


# 403 Forbidden
class PermissionDenied(DomainError):
    """Authenticated user lacks permission (e.g. not OWNER) to perform action."""

    status_code: int = 403


# 409 Conflict
class ConflictError(DomainError):
    """Base class for state conflict errors (HTTP 409)."""

    status_code: int = 409


class LoginTaken(ConflictError):
    """Attempted registration with a login that is already taken."""


class UserAlreadyMember(ConflictError):
    """Attempted invitation for a user who is already a project member."""


# 401 Unauthorized
class AuthenticationError(DomainError):
    """Authentication failed due to invalid credentials."""

    status_code: int = 401


class InvalidCredentials(AuthenticationError):
    """Supplied login or password does not match."""


# 413 Payload Too Large
class PayloadTooLargeError(DomainError):
    """Base class for file/quota size limit violations (HTTP 413)."""

    status_code: int = 413


class FileTooLarge(PayloadTooLargeError):
    """Uploaded file exceeds maximum allowed file size."""


class ProjectQuotaExceeded(PayloadTooLargeError):
    """Upload would exceed the total project size quota."""


# 400 Bad Request
class ValidationError(DomainError):
    """Base class for domain input and file format validation failures (HTTP 400)."""

    status_code: int = 400


class EmptyFilenameError(ValidationError):
    """Uploaded filename is empty or whitespace-only."""


class EmptyFileError(ValidationError):
    """Uploaded file is empty (0 bytes)."""


class NoFilesProvidedError(ValidationError):
    """Upload endpoint received no files."""


class InvalidFileExtension(ValidationError):
    """File extension is not in the allowed list."""


class InvalidFileSignature(ValidationError):
    """File magic bytes do not match declared extension/MIME type."""
