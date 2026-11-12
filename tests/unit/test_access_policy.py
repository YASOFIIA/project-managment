"""Unit tests for domain access policy and permission matrix."""

import pytest

from app.domain.access_policy import POLICY_MATRIX, Action, can_perform
from app.domain.roles import ProjectRole


def test_owner_policy_allows_all_actions() -> None:
    """Verify that ProjectRole.OWNER has permission for every Action."""
    assert POLICY_MATRIX[ProjectRole.OWNER] == frozenset(Action)
    for action in Action:
        assert can_perform(ProjectRole.OWNER, action) is True


def test_participant_policy_forbids_only_delete_and_invite() -> None:
    """Verify ProjectRole.PARTICIPANT is forbidden strictly DELETE_PROJECT and INVITE_MEMBER."""
    forbidden = {Action.DELETE_PROJECT, Action.INVITE_MEMBER}
    expected_allowed = frozenset(action for action in Action if action not in forbidden)

    assert POLICY_MATRIX[ProjectRole.PARTICIPANT] == expected_allowed
    assert can_perform(ProjectRole.PARTICIPANT, Action.DELETE_PROJECT) is False
    assert can_perform(ProjectRole.PARTICIPANT, Action.INVITE_MEMBER) is False


@pytest.mark.parametrize("action", list(Action))
def test_access_policy_owner_matrix_table(action: Action) -> None:
    """Parametrized check that OWNER can perform all actions."""
    assert can_perform(ProjectRole.OWNER, action) is True


@pytest.mark.parametrize("action", list(Action))
def test_access_policy_participant_matrix_table(action: Action) -> None:
    """Parametrized check that PARTICIPANT can perform non-destructive, non-admin actions."""
    if action in (Action.DELETE_PROJECT, Action.INVITE_MEMBER):
        assert can_perform(ProjectRole.PARTICIPANT, action) is False
    else:
        assert can_perform(ProjectRole.PARTICIPANT, action) is True
