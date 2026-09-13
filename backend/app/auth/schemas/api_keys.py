"""API key schemas — creation, read, list."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_SCOPES = {"read:models", "read:categories", "read:providers", "read:locales"}


class APIKeyCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=100, description="Human-readable key name")
    scopes: list[str] = Field(default_factory=lambda: ["read:models"])
    rate_limit_rpm: int = Field(default=60, ge=1, le=500)
    expires_at: datetime | None = Field(default=None, description="Optional expiration date")

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: list[str]) -> list[str]:
        if not v:
            return ["read:models"]
        for scope in v:
            if scope not in ALLOWED_SCOPES:
                # Mirror spec error message
                raise ValueError("API keys cannot have write scopes")
            if scope.startswith("write:") or scope.startswith("admin"):
                raise ValueError("API keys cannot have write scopes")
        return v


class APIKeyRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    name: str
    scopes: list[str]
    rate_limit_rpm: int
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


class APIKeyCreateResponse(APIKeyRead):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    key: str  # full key, only on creation


class APIKeyList(BaseModel):
    model_config = ConfigDict(frozen=True)

    data: list[APIKeyRead]
    total: int
