# Domain exceptions for project management
from __future__ import annotations


# Base class for domain business errors
class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
        self.detail = message


# Core Domain Categories (Pure business categories without HTTP knowledge)
# Base category for missing or hidden entities
class NotFoundError(DomainError):
    pass


# Base category for unique state collisions
class AlreadyExistsError(DomainError):
    pass


# Base category for permission errors
class PermissionDeniedError(DomainError):
    pass


# Base category for authentication errors
class AuthenticationError(DomainError):
    pass


# Base category for invalid input errors
class InvalidInputError(DomainError):
    pass


# Base category for limit violations
class LimitExceededError(DomainError):
    pass


# Concrete Resource Not Found Errors
# Project not found or hidden
class ProjectNotFound(NotFoundError):
    pass


# Document not found or hidden
class DocumentNotFound(NotFoundError):
    pass


# User not found
class UserNotFound(NotFoundError):
    pass


# Storage file not found
class StorageFileNotFound(NotFoundError):
    pass


# Invalid or used invitation token
class InvalidInvitationError(NotFoundError):
    pass


# Invitation token has expired
class InvitationExpiredError(DomainError):
    pass


# Concrete Authorization Errors
# Permission denied for non-owner
class PermissionDenied(PermissionDeniedError):
    pass


# Concrete Conflict / Already Exists Errors
# Login already taken
class LoginTaken(AlreadyExistsError):
    pass


# Email already taken
class EmailTaken(AlreadyExistsError):
    pass


# User is already a project member
class UserAlreadyMember(AlreadyExistsError):
    pass


# Concrete Authentication Errors
# Invalid login credentials
class InvalidCredentials(AuthenticationError):
    pass


# Concrete Limit Exceeded Errors
# Uploaded file exceeds size limit
class FileTooLarge(LimitExceededError):
    pass


# Upload exceeds project quota
class ProjectQuotaExceeded(LimitExceededError):
    pass


# Concrete Input Validation Errors
# Filename is empty
class EmptyFilenameError(InvalidInputError):
    pass


# File is empty (0 bytes)
class EmptyFileError(InvalidInputError):
    pass


# No files provided in request
class NoFilesProvidedError(InvalidInputError):
    pass


# File extension is not allowed
class InvalidFileExtension(InvalidInputError):
    pass


# File signature mismatch
class InvalidFileSignature(InvalidInputError):
    pass
