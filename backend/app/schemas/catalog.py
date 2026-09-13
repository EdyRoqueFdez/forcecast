from datetime import date
from decimal import Decimal
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class ModelModality(StrEnum):
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    CODE = "code"
    REASONING = "reasoning"


class CatalogModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    display_name: str
    provider: str
    family: str | None = None
    modalities: list[ModelModality]
    context_window: int | None = Field(default=None, gt=0)
    input_price_per_mtok: Decimal | None = Field(default=None, ge=0)
    output_price_per_mtok: Decimal | None = Field(default=None, ge=0)
    release_date: date | None = None
    categories: list[str]
    status: str = "approved"
    source: str = "manual"


class CatalogPage(BaseModel):
    items: list[CatalogModel]
    total: int
    limit: int
    offset: int


class ComparisonResponse(BaseModel):
    items: list[CatalogModel]
    missing_slugs: list[str]
