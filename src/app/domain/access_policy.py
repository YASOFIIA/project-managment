# Access policy — permission matrix for project roles
from enum import StrEnum

from app.domain.roles import ProjectRole


# Domain actions within project context
class Action(StrEnum):
    VIEW = "view"
    EDIT = "edit"
    DELETE_PROJECT = "delete_project"
    LIST_DOCUMENTS = "list_documents"
    UPLOAD_DOCUMENT = "upload_document"
    DOWNLOAD_DOCUMENT = "download_document"
    REPLACE_DOCUMENT = "replace_document"
    DELETE_DOCUMENT = "delete_document"
    INVITE_MEMBER = "invite_member"


POLICY_MATRIX: dict[ProjectRole, frozenset[Action]] = {
    ProjectRole.OWNER: frozenset(Action),
    ProjectRole.PARTICIPANT: frozenset(
        action for action in Action if action not in {Action.DELETE_PROJECT, Action.INVITE_MEMBER}
    ),
}


# Check if role is allowed to perform action
def can_perform(role: ProjectRole, action: Action) -> bool:
    return action in POLICY_MATRIX.get(role, frozenset())
