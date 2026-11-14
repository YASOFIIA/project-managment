from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.roles import ProjectRole
from app.schemas.document import DocumentResponse

ProjectName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class ProjectCreateRequest(BaseModel):
    """Payload for creating a new project via POST /projects."""

    name: ProjectName = Field(..., description="Project title")
    description: str | None = Field(default=None, description="Optional project description")


class ProjectUpdateRequest(BaseModel):
    """Payload for updating project details via PUT /project/<id>/info."""

    name: ProjectName = Field(..., description="Updated project title")
    description: str | None = Field(default=None, description="Updated project description")


class ProjectResponse(BaseModel):
    """Project details response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    total_size_bytes: int
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    """Detailed project model including attached documents list for GET /projects."""

    documents: list[DocumentResponse] = Field(default_factory=list)


class ProjectMemberResponse(BaseModel):
    """Membership details returned upon project member invitation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role: ProjectRole
    created_at: datetime


class InvitationResponse(BaseModel):
    """Payload returned when project share invitation is created and dispatched."""

    model_config = ConfigDict(from_attributes=True)

    message: str = Field(default="Invitation sent", description="Status message")
    email: str = Field(description="Invited recipient email address")
    expires_in_hours: int = Field(default=48, description="Hours until invitation token expires")
