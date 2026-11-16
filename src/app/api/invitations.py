from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, UowDep
from app.schemas.project import PendingInvitationResponse, ProjectMemberResponse
from app.services.invitations import (
    accept_invitation,
    accept_invitation_by_id,
    decline_invitation_by_id,
    list_pending_invitations_for_email,
)

router = APIRouter(tags=["Invitations"])


# Join project endpoint via invitation token
@router.get(
    "/join",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept project invitation",
    description="Join a project as participant using a valid share token. Requires authentication.",
)
def join_project_via_token(
    current_user: CurrentUser,
    uow: UowDep,
    token: Annotated[str, Query(min_length=1, description="Invitation share token")],
) -> ProjectMemberResponse:
    membership = accept_invitation(
        uow=uow,
        token=token,
        user_id=current_user.id,
    )
    return ProjectMemberResponse.model_validate(membership)


# List pending invitations for the current user's email
@router.get(
    "/invitations",
    response_model=list[PendingInvitationResponse],
    status_code=status.HTTP_200_OK,
    summary="List pending invitations",
    description=(
        "List all pending (not used, not expired) invitations for the current user's email."
    ),
)
def list_pending_invitations(
    current_user: CurrentUser,
    uow: UowDep,
) -> list[PendingInvitationResponse]:
    return list_pending_invitations_for_email(uow=uow, email=current_user.email)


# Accept a pending invitation by ID
@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept invitation by ID",
    description="Accept a pending invitation. The user is added as participant.",
)
def accept_pending_invitation(
    invitation_id: int,
    current_user: CurrentUser,
    uow: UowDep,
) -> ProjectMemberResponse:
    membership = accept_invitation_by_id(
        uow=uow,
        invitation_id=invitation_id,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return ProjectMemberResponse.model_validate(membership)


# Decline a pending invitation by ID
@router.post(
    "/invitations/{invitation_id}/decline",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Decline invitation",
    description="Mark an invitation as used (declined) so it no longer appears in pending list.",
)
def decline_pending_invitation(
    invitation_id: int,
    current_user: CurrentUser,
    uow: UowDep,
) -> None:
    decline_invitation_by_id(
        uow=uow,
        invitation_id=invitation_id,
        user_email=current_user.email,
    )
