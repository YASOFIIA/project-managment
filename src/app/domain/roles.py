"""Domain role definitions."""

from enum import StrEnum


class ProjectRole(StrEnum):
    """Role of a member within a project boundary."""

    OWNER = "owner"
    PARTICIPANT = "participant"
