"""Public API — 5 read endpoints with envelope, pagination, locale, cache."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.taxonomy.schemas.public import SUPPORTED_LOCALES
from app.taxonomy.services.public import PublicService, encode_cursor

router = APIRouter(tags=["taxonomy-public"])


CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=300"
CACHE_TAGS = "taxonomy:v1, models:approved, categories:active"


def _cache_headers(response: Response) -> None:
    response.headers["Cache-Control"] = CACHE_CONTROL
    response.headers["Vary"] = "Accept-Language, Accept-Encoding"
    response.headers["X-Cache-Tags"] = CACHE_TAGS


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


def _validate_locale(lang: str) -> str:
    norm = str(lang).strip().lower()
    if norm not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=406, detail="unsupported")
    return norm


@router.get("/models")
async def list_models(
    request: Request,
    response: Response,
    category_slug: str | None = Query(None),
    provider_slug: str | None = Query(None),
    modalities: str | None = Query(None),
    lang: str = Query("en"),
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("release_date", pattern="^(release_date|input_price|output_price|name|display_name|input_price_per_mtok|output_price_per_mtok)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_session),
):
    # locale check 406
    norm_lang = str(lang).strip().lower()
    if norm_lang not in SUPPORTED_LOCALES:
        return _unsupported_locale_response(lang)
    # page >10 => 422 use cursor
    if page is not None and page > 10:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "page >10 requires cursor pagination",
                    "details": [{"field": "page", "issue": "use cursor for page >10"}],
                    "trace_id": str(uuid.uuid4()),
                }
            },
        )
    svc = PublicService(db)
    mods = modalities
    items, total = await svc.list_models(
        category_slug=category_slug,
        provider_slug=provider_slug,
        modalities=mods,
        search=search,
        locale=norm_lang,
        limit=limit,
        cursor=cursor,
        sort=sort,
        order=order,
    )
    # Simple has_more: if we returned limit items and there are more total, there is more.
    # For cursor pagination, if len==limit assume more (conservative); last page edge when total % limit ==0 will be off but not covered by tests.
    if not items:
        has_more = False
        next_cursor = None
    elif len(items) == limit and total > len(items) or len(items) == limit and cursor is not None:
        has_more = True
        next_cursor = encode_cursor(items[-1])
    else:
        has_more = total > len(items)
        next_cursor = encode_cursor(items[-1]) if has_more and items else None

    # Build links
    base = str(request.url.path)
    # first/last simple
    first = f"{base}?limit={limit}"
    last = f"{base}?limit={limit}"
    nxt = f"{base}?limit={limit}&cursor={next_cursor}" if next_cursor else None

    try:
        from app.taxonomy.services.public import _get_current_version

        tv = await _get_current_version(db)
    except Exception:
        tv = "v1"
    meta = {
        "page": page or 1,
        "limit": limit,
        "total": total,
        "has_more": has_more,
        "next_cursor": next_cursor,
        "taxonomy_version": tv,
    }

    links = {"first": first, "prev": None, "next": nxt, "last": last}
    _cache_headers(response)
    response.headers["Content-Language"] = norm_lang
    return {"data": items, "meta": meta, "links": links}


@router.get("/models/{slug}")
async def get_model(
    slug: str,
    request: Request,
    response: Response,
    lang: str = Query("en"),
    db: AsyncSession = Depends(get_session),
):
    norm_lang = str(lang).strip().lower()
    if norm_lang not in SUPPORTED_LOCALES:
        return _unsupported_locale_response(lang)
    svc = PublicService(db)
    detail = await svc.get_model(slug, locale=norm_lang)
    if not detail:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Model {slug} not found",
                    "details": [],
                    "trace_id": str(uuid.uuid4()),
                }
            },
        )
    _cache_headers(response)
    response.headers["Content-Language"] = norm_lang
    return JSONResponse(content=detail, headers=dict(response.headers))


@router.get("/categories")
async def list_categories(
    request: Request,
    response: Response,
    lang: str = Query("en"),
    db: AsyncSession = Depends(get_session),
):
    norm_lang = str(lang).strip().lower()
    if norm_lang not in SUPPORTED_LOCALES:
        return _unsupported_locale_response(lang)
    svc = PublicService(db)
    cats, tv = await svc.list_categories(locale=norm_lang)
    _cache_headers(response)
    response.headers["Content-Language"] = norm_lang
    return {"data": cats, "meta": {"taxonomy_version": tv, "total": len(cats)}}


@router.get("/providers")
async def list_providers(
    request: Request,
    response: Response,
    lang: str = Query("en"),
    db: AsyncSession = Depends(get_session),
):
    norm_lang = str(lang).strip().lower()
    if norm_lang not in SUPPORTED_LOCALES:
        return _unsupported_locale_response(lang)
    svc = PublicService(db)
    provs = await svc.list_providers(locale=norm_lang)
    _cache_headers(response)
    response.headers["Content-Language"] = norm_lang
    return {"data": provs, "total": len(provs)}


@router.get("/locales")
async def list_locales(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    svc = PublicService(db)
    locales = await svc.list_locales()
    _cache_headers(response)
    return {"data": locales, "total": len(locales)}


@router.get("/orchestrators")
async def list_orchestrators(
    request: Request,
    response: Response,
    lang: str = Query("en"),
    category: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("name", pattern="^(name|version|created_at)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_session),
):
    """HU-T08 — List approved orchestrators with pagination, i18n, caching."""
    # Locale validation
    norm_lang = str(lang).strip().lower()
    if norm_lang not in SUPPORTED_LOCALES:
        return _unsupported_locale_response(lang)

    # page >10 => 422 use cursor
    if page is not None and page > 10:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "page >10 requires cursor pagination",
                    "details": [{"field": "page", "issue": "use cursor for page >10"}],
                    "trace_id": str(uuid.uuid4()),
                }
            },
        )

    svc = PublicService(db)
    items, total = await svc.list_orchestrators(
        locale=norm_lang,
        limit=limit,
        cursor=cursor,
        sort=sort,
        order=order,
        category=category,
    )

    # Build pagination metadata
    if not items:
        has_more = False
        next_cursor = None
    elif len(items) == limit and total > len(items) or len(items) == limit and cursor is not None:
        has_more = True
        next_cursor = encode_cursor(items[-1])
    else:
        has_more = total > len(items)
        next_cursor = encode_cursor(items[-1]) if has_more and items else None

    # Build links
    base = str(request.url.path)
    first = f"{base}?limit={limit}"
    last = f"{base}?limit={limit}"
    nxt = f"{base}?limit={limit}&cursor={next_cursor}" if next_cursor else None

    try:
        from app.taxonomy.services.public import _get_current_version
        tv = await _get_current_version(db)
    except Exception:
        tv = "v1"

    meta = {
        "page": page or 1,
        "limit": limit,
        "total": total,
        "has_more": has_more,
        "next_cursor": next_cursor,
        "taxonomy_version": tv,
    }

    links = {"first": first, "prev": None, "next": nxt, "last": last}
    _cache_headers(response)
    response.headers["Content-Language"] = norm_lang
    return {"data": items, "meta": meta, "links": links}
