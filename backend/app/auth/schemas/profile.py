"""Profile schemas — request/response models for user profile."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    """Response schema for GET /auth/me."""
    id: str
    email: str | None
    display_name: str
    avatar_url: str | None
    role: str
    reputation_score: float
    email_verified: bool
    bio: str | None
    preferred_locale: str
    visibility_mode: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    """Request schema for PATCH /auth/me."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=500)
    preferred_locale: Optional[str] = Field(None, pattern=r"^(en|es|pt|fr|zh)$")
    visibility_mode: Optional[str] = Field(None, pattern=r"^(pseudonym|public)$")


class ProfileUpdateResponse(BaseModel):
    """Response schema for PATCH /auth/me."""
    message: str = "Profile updated"
    profile: ProfileResponse
