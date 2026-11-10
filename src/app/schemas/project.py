from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentResponse


class ProjectCreateRequest(BaseModel):
    """Payload for creating a new project via POST /projects."""

    name: str = Field(..., min_length=1, max_length=255, description="Project title")
    description: str | None = Field(default=None, description="Optional project description")


class ProjectUpdateRequest(BaseModel):
    """Payload for updating project details via PUT /project/<id>/info."""

    name: str = Field(..., min_length=1, max_length=255, description="Updated project title")
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
