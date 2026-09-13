"""Public schemas — envelope, errors, model detail, locale negotiation."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Generic, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.taxonomy.models.enums import Locale

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pagination envelope
# ---------------------------------------------------------------------------


class Meta(BaseModel):
    page: int = 1
    limit: int = 20
    total: int
    has_more: bool
    next_cursor: str | None = None
    taxonomy_version: str | None = None


class Links(BaseModel):
    first: str
    prev: str | None = None
    next: str | None = None
    last: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: Meta
    links: Links


# ---------------------------------------------------------------------------
# Error envelope RFC7807-like
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ErrorResponse(BaseModel):
    error: ErrorEnvelope

    @classmethod
    def from_exception(cls, code: str, message: str, status_code: int = 400, details: list[ErrorDetail] | None = None) -> ErrorResponse:
        return cls(
            error=ErrorEnvelope(
                code=code,
                message=message,
                details=details or [],
                trace_id=str(uuid.uuid4()),
            )
        )


# ---------------------------------------------------------------------------
# Locale negotiation
# ---------------------------------------------------------------------------

SUPPORTED_LOCALES = {e.value for e in Locale}


def resolve_locale(lang: str) -> Locale:
    norm = str(lang).strip().lower()
    try:
        return Locale(norm)
    except ValueError:
        raise HTTPException(
            status_code=406,
            detail={
                "error": {
                    "code": "UNSUPPORTED_LOCALE",
                    "message": f"Unsupported locale: {lang}. Supported: {sorted(SUPPORTED_LOCALES)}",
                    "details": [],
                    "trace_id": str(uuid.uuid4()),
                }
            },
        )


def locale_error_response(lang: str) -> dict:
    return {
        "error": {
            "code": "UNSUPPORTED_LOCALE",
            "message": f"Unsupported locale: {lang}",
            "details": [{"field": "lang", "issue": f"must be one of {sorted(SUPPORTED_LOCALES)}"}],
            "trace_id": str(uuid.uuid4()),
        }
    }


# ---------------------------------------------------------------------------
# Model responses
# ---------------------------------------------------------------------------


class ProviderSummary(BaseModel):
    slug: str
    name: str


class CategorySummary(BaseModel):
    slug: str
    name: str


class ModelHostingResponse(BaseModel):
    provider: ProviderSummary
    is_primary: bool


class ModelDetailResponse(BaseModel):
    id: str
    slug: str
    display_name: str
    version: str | None = None
    family: str | None = None
    modality: list[str]
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_price_per_mtok: Decimal | None = None
    output_price_per_mtok: Decimal | None = None
    release_date: str | None = None
    deprecation_date: str | None = None
    status: str
    source: str
    source_url: str | None = None
    categories: list[CategorySummary] = Field(default_factory=list)
    hostings: list[ModelHostingResponse] = Field(default_factory=list)
    locale_used: str = "en"
    description: str | None = None

    model_config = {"populate_by_name": True}


class ModelListItem(BaseModel):
    id: str
    slug: str
    display_name: str
    modality: list[str]
    status: str
    provider: ProviderSummary | None = None
    input_price_per_mtok: Decimal | None = None
    output_price_per_mtok: Decimal | None = None
    release_date: str | None = None
    categories: list[CategorySummary] = Field(default_factory=list)
    locale_used: str = "en"


class CategoryResponse(BaseModel):
    slug: str
    name: str
    description: str | None = None
    taxonomy_version: str
    locale_used: str = "en"


class ProviderResponse(BaseModel):
    slug: str
    name: str
    description: str | None = None
    website: str | None = None
    status: str
    locale_used: str = "en"


class LocaleMetaResponse(BaseModel):
    locale: str
    native_name: str
    direction: str
    plural_categories: list[str]
