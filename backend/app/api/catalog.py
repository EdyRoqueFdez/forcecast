from fastapi import APIRouter, Query

from app.schemas.catalog import CatalogPage, ComparisonResponse, ModelModality
from app.services.catalog import compare_models, list_models

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/models", response_model=CatalogPage)
async def get_models(
    query: str | None = Query(default=None, min_length=1, max_length=100),
    category: str | None = Query(default=None, min_length=1, max_length=50),
    modality: ModelModality | None = None,
    provider: str | None = Query(default=None, min_length=1, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CatalogPage:
    items, total = list_models(
        query=query,
        category=category,
        modality=modality,
        provider=provider,
        limit=limit,
        offset=offset,
    )
    return CatalogPage(items=list(items), total=total, limit=limit, offset=offset)


@router.get("/models/compare", response_model=ComparisonResponse)
async def compare_model_list(
    slugs: list[str] = Query(..., min_length=1, max_length=4),
) -> ComparisonResponse:
    items, missing_slugs = compare_models(slugs)
    return ComparisonResponse(items=items, missing_slugs=missing_slugs)
