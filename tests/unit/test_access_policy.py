# Tests for domain access policy
import pytest

from app.domain.access_policy import POLICY_MATRIX, Action, can_perform
from app.domain.roles import ProjectRole


# Check ProjectRole.OWNER has permission for every Action
def test_owner_policy_allows_all_actions() -> None:
    assert POLICY_MATRIX[ProjectRole.OWNER] == frozenset(Action)
    for action in Action:
        assert can_perform(ProjectRole.OWNER, action) is True


# Check ProjectRole.PARTICIPANT is forbidden DELETE_PROJECT, INVITE_MEMBER, and REMOVE_MEMBER
def test_participant_policy_forbids_only_delete_and_invite() -> None:
    forbidden = {Action.DELETE_PROJECT, Action.INVITE_MEMBER, Action.REMOVE_MEMBER}
    expected_allowed = frozenset(action for action in Action if action not in forbidden)

    assert POLICY_MATRIX[ProjectRole.PARTICIPANT] == expected_allowed
    assert can_perform(ProjectRole.PARTICIPANT, Action.DELETE_PROJECT) is False
    assert can_perform(ProjectRole.PARTICIPANT, Action.INVITE_MEMBER) is False
    assert can_perform(ProjectRole.PARTICIPANT, Action.REMOVE_MEMBER) is False


# Parametrized check that OWNER can perform all actions
@pytest.mark.parametrize("action", list(Action))
def test_access_policy_owner_matrix_table(action: Action) -> None:
    assert can_perform(ProjectRole.OWNER, action) is True


# Parametrized check that PARTICIPANT can perform non-destructive, non-admin actions
@pytest.mark.parametrize("action", list(Action))
def test_access_policy_participant_matrix_table(action: Action) -> None:
    if action in (Action.DELETE_PROJECT, Action.INVITE_MEMBER, Action.REMOVE_MEMBER):
        assert can_perform(ProjectRole.PARTICIPANT, action) is False
    else:
        assert can_perform(ProjectRole.PARTICIPANT, action) is True
