import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.auth.models.user import RoleEnum


class UserRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: uuid.UUID
    email: str | None
    display_name: str
    avatar_url: str | None
    role: RoleEnum
    reputation_score: float
    email_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)


class OAuthCallback(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class DeviceFingerprintInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_agent: str = Field(min_length=1)
    ip_address: str = Field(min_length=1)
    accept_language: str = Field(min_length=1)
