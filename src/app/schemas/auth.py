from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Registration request payload
class UserRegisterRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=64, description="Unique username")
    password: str = Field(..., min_length=6, description="Raw user password")
    repeat_password: str = Field(..., min_length=6, description="Password confirmation")

    # Validate matching passwords
    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.password != self.repeat_password:
            raise ValueError("Passwords do not match")
        return self


# Login request payload
class UserLoginRequest(BaseModel):
    login: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="User password")


# JWT token response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Public user profile response
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    created_at: datetime
