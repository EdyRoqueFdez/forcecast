"""Vote schemas — Pydantic models for API request/response."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VoteRequest(BaseModel):
    """Request body for casting or changing a vote."""

    target_type: Literal["model", "orchestrator"]
    target_id: str = Field(..., max_length=36, description="UUID of the target")
    category_id: str = Field(..., max_length=36, description="UUID of the category")
    idempotency_key: str = Field(
        ..., max_length=255, description="Unique key for idempotency"
    )
    turnstile_token: str | None = Field(
        None, max_length=1000, description="Cloudflare Turnstile token (required when CAPTCHA triggered)"
    )

    @field_validator("target_id", "category_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate UUID format."""
        try:
            parts = v.split("-")
            if len(parts) != 5:
                raise ValueError("Invalid UUID format")
            if len(parts[0]) != 8 or len(parts[3]) != 4 or len(parts[4]) != 12:
                raise ValueError("Invalid UUID format")
            # Validate hex characters
            for part in parts:
                int(part, 16)
            return v
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid UUID format: {v}") from e


class VoteResponse(BaseModel):
    """Response body for vote operations."""

    id: str
    user_id: str
    target_type: str
    target_id: str
    category_id: str
    action: str
    weight: Decimal
    created_at: datetime | None = None


class UserVoteItem(BaseModel):
    """Single user vote item."""

    category_id: str
    target_type: str
    target_id: str
    weight: Decimal
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserVotesResponse(BaseModel):
    """Response body for listing user votes."""

    votes: list[UserVoteItem]


class CategoryVoteCount(BaseModel):
    """Vote count for a single category."""

    category_id: str
    votes: int
    weighted_score: Decimal


class ModelVotesResponse(BaseModel):
    """Response body for model vote count."""

    target_type: str
    target_id: str
    total_votes: int
    weighted_score: Decimal
