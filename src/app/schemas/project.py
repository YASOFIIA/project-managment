from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.roles import ProjectRole
from app.schemas.document import DocumentResponse

ProjectName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


# Request payload for project creation
class ProjectCreateRequest(BaseModel):
    name: ProjectName = Field(..., description="Project title")
    description: str | None = Field(default=None, description="Optional project description")


# Request payload for project update
class ProjectUpdateRequest(BaseModel):
    name: ProjectName = Field(..., description="Updated project title")
    description: str | None = Field(default=None, description="Updated project description")


# Project details response
class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    total_size_bytes: int
    created_at: datetime
    updated_at: datetime


# Project detail response with documents
class ProjectDetailResponse(ProjectResponse):
    documents: list[DocumentResponse] = Field(default_factory=list)


# Project member response
class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role: ProjectRole
    created_at: datetime


# Response after sending email invitation
class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(default="Invitation sent", description="Status message")
    email: str = Field(description="Invited recipient email address")
    expires_in_hours: int = Field(default=48, description="Hours until invitation token expires")
