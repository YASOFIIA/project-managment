from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Document metadata response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str
    file_size_bytes: int
    content_type: str
    created_at: datetime
