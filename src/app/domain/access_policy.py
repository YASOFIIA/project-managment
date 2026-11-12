"""Pure domain access policy and permission matrix.

Evaluates whether a given ProjectRole has permission to perform an Action.
This module is pure domain logic: zero dependencies on database sessions, ORM, or HTTP.
"""

from enum import StrEnum

from app.domain.roles import ProjectRole


class Action(StrEnum):
    """Domain actions within a project context."""

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


def can_perform(role: ProjectRole, action: Action) -> bool:
    """Pure domain function determining if role is allowed to perform action.

    Args:
        role: The project role assigned to the user.
        action: The requested domain action.

    Returns:
        True if the action is permitted for the role, False otherwise.
    """
    return action in POLICY_MATRIX.get(role, frozenset())
