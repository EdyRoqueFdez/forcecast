"""Anti-bot schemas — Turnstile verification and anomaly events."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TurnstileVerifyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    token: str = Field(min_length=1, description="Turnstile/hCaptcha token")
    remote_ip: str | None = Field(default=None, description="Client IP for verification")


class TurnstileVerifyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    error_codes: list[str] | None = None


class RateLimitInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    limit: int
    remaining: int
    retry_after: int


class AnomalyEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str = Field(min_length=1, description="Anomaly type")
    user_id: str | None = Field(default=None)
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = Field(default=None)
