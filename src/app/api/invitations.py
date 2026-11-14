from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, UowDep
from app.schemas.project import ProjectMemberResponse
from app.services.invitations import accept_invitation

router = APIRouter(tags=["Invitations"])


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
    """Join project endpoint via email invitation token."""
    membership = accept_invitation(
        uow=uow,
        token=token,
        user_id=current_user.id,
    )
    return ProjectMemberResponse.model_validate(membership)
