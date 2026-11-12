"""Domain exception hierarchy for the Project Management domain.

Pure domain exceptions with no dependencies on HTTP frameworks or status codes.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain business errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
        self.detail = message


# Core Domain Categories (Pure business categories without HTTP knowledge)
class NotFoundError(DomainError):
    """Base category for entities that do not exist or are hidden for security."""


class AlreadyExistsError(DomainError):
    """Base category for entity identity or unique state collisions."""


class PermissionDeniedError(DomainError):
    """Base category for business operations rejected due to insufficient privileges."""


class AuthenticationError(DomainError):
    """Base category for credential verification or identity authentication failures."""


class InvalidInputError(DomainError):
    """Base category for malformed, empty, or unparseable input data."""


class LimitExceededError(DomainError):
    """Base category for quota, storage, or volume limit violations."""


# Concrete Resource Not Found Errors
class ProjectNotFound(NotFoundError):
    """Project does not exist or user has no access (information hiding)."""


class DocumentNotFound(NotFoundError):
    """Document does not exist or user has no access (information hiding)."""


class UserNotFound(NotFoundError):
    """Target user (e.g. invitee) does not exist."""


class StorageFileNotFound(NotFoundError):
    """File record exists in database, but physical object is missing from storage."""


# Concrete Authorization Errors
class PermissionDenied(PermissionDeniedError):
    """Authenticated user lacks permission (e.g. not OWNER) to perform action."""


# Concrete Conflict / Already Exists Errors
class LoginTaken(AlreadyExistsError):
    """Attempted registration with a login that is already taken."""


class UserAlreadyMember(AlreadyExistsError):
    """Attempted invitation for a user who is already a project member."""


# Concrete Authentication Errors
class InvalidCredentials(AuthenticationError):
    """Supplied login or password does not match."""


# Concrete Limit Exceeded Errors
class FileTooLarge(LimitExceededError):
    """Uploaded file exceeds maximum allowed file size."""


class ProjectQuotaExceeded(LimitExceededError):
    """Upload would exceed the total project size quota."""


# Concrete Input Validation Errors
class EmptyFilenameError(InvalidInputError):
    """Uploaded filename is empty or whitespace-only."""


class EmptyFileError(InvalidInputError):
    """Uploaded file is empty (0 bytes)."""


class NoFilesProvidedError(InvalidInputError):
    """Upload endpoint received no files."""


class InvalidFileExtension(InvalidInputError):
    """File extension is not in the allowed list."""


class InvalidFileSignature(InvalidInputError):
    """File magic bytes do not match declared extension/MIME type."""
