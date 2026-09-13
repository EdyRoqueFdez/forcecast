"""
Forcecast MVP - AI Model Catalog & Comparator
Auth integration (Phase 7): routers wired, CORS, admin protection.
"""
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum

from app.core.config import settings

from app.auth.api.oauth import router as oauth_router
from app.auth.api.tokens import router as tokens_router
from app.auth.api.api_keys import router as api_keys_router
from app.auth.api.profile import router as profile_router
from app.auth.api.verification import router as verification_router
from app.api.admin import router as admin_router
from app.voting.api.votes import router as votes_router
from app.voting.api.rankings import router as rankings_router

# Load models from JSON at startup
DATA_PATH = Path(__file__).parent / "data" / "models.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    MODELS_DATA = json.load(f)

# Build lookup indices
MODELS_BY_SLUG = {m["slug"]: m for m in MODELS_DATA}
CATEGORIES = sorted({cat for m in MODELS_DATA for cat in m.get("categories", [])})
PROVIDERS = sorted({m["provider"]["slug"] for m in MODELS_DATA})
MODALITIES = sorted({mod for m in MODELS_DATA for mod in m.get("modality", [])})

app = FastAPI(
    title="Forcecast MVP",
    version="0.1.0-mvp",
    description="AI Model Catalog & Comparator - Validation MVP",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — use configured origins; if "*" not allowed with credentials, resolve to explicit list
cors_origins = settings.CORS_ORIGINS if hasattr(settings, "CORS_ORIGINS") else ["http://localhost:3000", "http://localhost:5173"]
# Ensure auth origins included if not wildcard
if cors_origins == ["*"]:
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = cors_origins
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(oauth_router)
app.include_router(tokens_router)
app.include_router(api_keys_router)
app.include_router(profile_router)
app.include_router(verification_router)
app.include_router(admin_router)
app.include_router(votes_router)
app.include_router(rankings_router)


class SortField(str, Enum):
    release_date = "release_date"
    input_price = "input_price_per_mtok"
    output_price = "output_price_per_mtok"
    name = "display_name"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class ModelResponse(BaseModel):
    slug: str
    display_name: str
    provider: dict
    family: str
    version: str
    modality: list[str]
    context_window: int
    max_output_tokens: int
    input_price_per_mtok: Optional[float] = None
    output_price_per_mtok: Optional[float] = None
    release_date: str
    status: str
    categories: list[str]
    source: str
    source_url: str


class CompareResponse(BaseModel):
    models: list[ModelResponse]
    count: int
    missing: list[str]


class ModelsListResponse(BaseModel):
    data: list[ModelResponse]
    total: int
    limit: int
    offset: int


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0-mvp", "models_loaded": len(MODELS_DATA)}


@app.get("/api/v1/models", response_model=ModelsListResponse)
async def list_models(
    category: Optional[str] = Query(None, description="Filter by category slug"),
    provider: Optional[str] = Query(None, description="Filter by provider slug"),
    modality: Optional[str] = Query(None, description="Filter by modality"),
    search: Optional[str] = Query(None, description="Search in name, slug, family"),
    sort: SortField = Query(SortField.release_date, description="Sort field"),
    order: SortOrder = Query(SortOrder.desc, description="Sort order"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List approved models with filtering, search, and pagination."""
    results = MODELS_DATA

    # Filters
    if category:
        results = [m for m in results if category in m.get("categories", [])]
    if provider:
        results = [m for m in results if m["provider"]["slug"] == provider]
    if modality:
        results = [m for m in results if modality in m.get("modality", [])]
    if search:
        search_lower = search.lower()
        results = [
            m for m in results
            if search_lower in m["slug"].lower()
            or search_lower in m["display_name"].lower()
            or search_lower in m.get("family", "").lower()
        ]

    # Sort
    reverse = order == SortOrder.desc
    if sort == SortField.input_price:
        results.sort(key=lambda m: (m.get("input_price_per_mtok") is None, m.get("input_price_per_mtok") or 0), reverse=reverse)
    elif sort == SortField.output_price:
        results.sort(key=lambda m: (m.get("output_price_per_mtok") is None, m.get("output_price_per_mtok") or 0), reverse=reverse)
    elif sort == SortField.name:
        results.sort(key=lambda m: m["display_name"].lower(), reverse=reverse)
    else:  # release_date
        results.sort(key=lambda m: m.get("release_date", ""), reverse=reverse)

    total = len(results)
    paginated = results[offset:offset + limit]

    return ModelsListResponse(
        data=[ModelResponse(**m) for m in paginated],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/models/compare", response_model=CompareResponse)
async def compare_models(slugs: list[str] = Query(..., description="Model slugs to compare (2-4)")):
    """Compare 2-4 models side by side."""
    if len(slugs) < 2 or len(slugs) > 4:
        raise HTTPException(400, "Provide 2 to 4 slugs to compare")

    found = []
    missing = []
    for slug in slugs:
        model = MODELS_BY_SLUG.get(slug)
        if model and model["status"] == "approved":
            found.append(ModelResponse(**model))
        else:
            missing.append(slug)

    return CompareResponse(models=found, count=len(found), missing=missing)


@app.get("/api/v1/models/{slug}", response_model=ModelResponse)
async def get_model(slug: str):
    """Get single model detail."""
    model = MODELS_BY_SLUG.get(slug)
    if not model or model["status"] != "approved":
        raise HTTPException(404, "Model not found")
    return ModelResponse(**model)


@app.get("/api/v1/categories")
async def list_categories():
    """List available categories."""
    return {"data": CATEGORIES, "total": len(CATEGORIES)}


@app.get("/api/v1/providers")
async def list_providers():
    """List available providers."""
    provider_details = {}
    for m in MODELS_DATA:
        slug = m["provider"]["slug"]
        if slug not in provider_details:
            provider_details[slug] = m["provider"]
    return {"data": list(provider_details.values()), "total": len(provider_details)}


@app.get("/api/v1/modalities")
async def list_modalities():
    """List available modalities."""
    return {"data": MODALITIES, "total": len(MODALITIES)}


@app.get("/api/v1/meta")
async def meta():
    """Metadata for UI: categories, providers, modalities, model count."""
    return {
        "categories": CATEGORIES,
        "providers": PROVIDERS,
        "modalities": MODALITIES,
        "total_models": len(MODELS_DATA),
        "version": "0.1.0-mvp",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
