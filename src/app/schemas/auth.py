from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserRegisterRequest(BaseModel):
    """Payload for user registration endpoint POST /auth."""

    login: str = Field(..., min_length=3, max_length=64, description="Unique username")
    password: str = Field(..., min_length=6, description="Raw user password")
    repeat_password: str = Field(..., min_length=6, description="Password confirmation")

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        """Validate that password and repeat_password are identical."""
        if self.password != self.repeat_password:
            raise ValueError("Passwords do not match")
        return self


class UserLoginRequest(BaseModel):
    """Payload for user authentication endpoint POST /login."""

    login: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="User password")


class TokenResponse(BaseModel):
    """Response returned upon successful authentication."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user profile information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    created_at: datetime
