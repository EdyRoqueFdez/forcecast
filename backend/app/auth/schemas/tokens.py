"""Token schemas — TokenPair, JWKS."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TokenPair(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)
    token_type: Literal["bearer"] = "bearer"


class RefreshRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    refresh_token: str | None = Field(default=None, min_length=1)


class JWK(BaseModel):
    model_config = ConfigDict(frozen=True)

    kty: str = "RSA"
    use: str = "sig"
    kid: str
    alg: str = "RS256"
    n: str
    e: str


class JWKSResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    keys: list[JWK]
