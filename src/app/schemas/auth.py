import re
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# Registration request payload
class UserRegisterRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=64, description="Unique username")
    email: str = Field(..., min_length=5, max_length=255, description="User email address")
    password: str = Field(..., min_length=6, description="Raw user password")
    repeat_password: str = Field(..., min_length=6, description="Password confirmation")

    # Validate email format
    @field_validator("email")
    @classmethod
    def check_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address")
        return clean

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
    email: str
    created_at: datetime
