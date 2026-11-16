from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Document metadata response
class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str
    file_size_bytes: int
    content_type: str
    created_at: datetime
