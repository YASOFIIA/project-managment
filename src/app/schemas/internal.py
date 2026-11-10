"""Pydantic schemas for internal API endpoints (e.g. Lambda callbacks)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LambdaQuotaCallbackRequest(BaseModel):
    """Payload received from the Lambda size_limit event handler."""

    model_config = ConfigDict(extra="forbid")

    project_id: int = Field(gt=0, description="Target project ID")
    document_id: int = Field(gt=0, description="Target document ID")
    filename: str = Field(min_length=1, description="Uploaded filename")
    status: Literal["accepted", "rejected"] = Field(description="Quota evaluation verdict")
    total_size_bytes: int = Field(
        ge=0, description="Calculated total size of all stored project objects"
    )
    limit_bytes: int = Field(gt=0, description="Configured quota limit in bytes")


class LambdaQuotaCallbackResponse(BaseModel):
    """Response returned to the Lambda webhook caller."""

    model_config = ConfigDict(extra="forbid")

    status: str
    message: str
    project_id: int
    document_id: int
    total_size_bytes: int
