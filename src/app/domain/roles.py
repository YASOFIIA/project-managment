# Domain role definitions
from enum import StrEnum


# Role of a member in a project
class ProjectRole(StrEnum):
    OWNER = "owner"
    PARTICIPANT = "participant"
