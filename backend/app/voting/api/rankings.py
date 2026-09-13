"""Ranking API routes — FastAPI router for ranking operations."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.taxonomy.schemas.public import SUPPORTED_LOCALES
from app.voting.services.ranking import RankingService

router = APIRouter(prefix="/api/v1", tags=["rankings"])


CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=900"


def _cache_headers(response: Response) -> None:
    response.headers["Cache-Control"] = CACHE_CONTROL
    response.headers["Vary"] = "Accept-Language, Accept-Encoding"


def _unsupported_locale_response(lang: str) -> JSONResponse:
    return JSONResponse(
        status_code=406,
        content={
            "error": {
                "code": "UNSUPPORTED_LOCALE",
                "message": f"Unsupported locale: {lang}. Supported: {sorted(SUPPORTED_LOCALES)}",
                "details": [{"field": "lang", "issue": f"must be one of {sorted(SUPPORTED_LOCALES)}"}],
                "trace_id": str(uuid.uuid4()),
            }
        },
        headers={
            "Link": ", ".join(f'<{v}>; rel="alternate"; hreflang="{v}"' for v in sorted(SUPPORTED_LOCALES)),
            "Content-Language": lang,
            "Vary": "Accept-Language",
        },
    )


@router.get("/rankings/models")
async def get_model_ranking(
    request: Request,
    response: Response,
    category: str = Query(..., description="Category slug"),
    lang: str = Query("en"),
    min_votes: int = Query(5, ge=1, description="Minimum votes required"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    """HU-V06 — Get model ranking for a category."""
    # Locale validation
    norm_lang = str(lang).strip().lower()
    if norm_lang not in SUPPORTED_LOCALES:
        return _unsupported_locale_response(lang)

    svc = RankingService(db)
    items, total = await svc.get_model_ranking(
        category_slug=category,
        locale=norm_lang,
        min_votes=min_votes,
        limit=limit,
        cursor=cursor,
    )

    # Build pagination metadata
    has_more = len(items) == limit and total > len(items)
    next_cursor = None
    if has_more and items:
        import base64
        import json
        last_item = items[-1]
        cursor_data = {"model_id": last_item["model_id"]}
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(cursor_data).encode()
        ).decode().rstrip("=")

    meta = {
        "category": category,
        "total": total,
        "has_more": has_more,
        "next_cursor": next_cursor,
        "min_votes": min_votes,
    }

    _cache_headers(response)
    response.headers["Content-Language"] = norm_lang
    return {"data": items, "meta": meta}
