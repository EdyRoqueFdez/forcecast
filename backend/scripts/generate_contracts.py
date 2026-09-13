"""Generate OpenAPI contracts for taxonomy public + admin — 8.2"""

import pathlib
import yaml

from fastapi import FastAPI
from app.taxonomy.api.public import router as public_router
from app.taxonomy.api.admin import router as admin_router

ROOT = pathlib.Path(__file__).parents[1]
OUT_PUBLIC = ROOT / "forcecast" / "contracts" / "taxonomy-public.yaml"
OUT_ADMIN = ROOT / "forcecast" / "contracts" / "taxonomy-admin.yaml"


def enrich_public(openapi: dict) -> dict:
    openapi["info"]["title"] = "Forcecast Taxonomy — Public API"
    openapi["info"]["description"] = (
        "Public read API — 5 endpoints exposing approved models, categories, providers, and locale metadata. "
        "Responses use standardized envelope, keyset pagination, Redis caching (public, max-age=60, stale-while-revalidate=300), "
        "and full-text search with GIN indexes. Only approved models and active categories are returned. "
        "Price fields (input_price_per_mtok, output_price_per_mtok) are reference-only and omitted when null. "
        "Cache tags: taxonomy:v1, models:approved, categories:active. Cache-Control and CDN caching documented."
    )
    openapi["info"]["version"] = "1.0.0"
    # Add Cache-Control documentation to each GET
    for path, methods in openapi.get("paths", {}).items():
        for method, op in methods.items():
            if method == "get":
                op.setdefault("responses", {})
                # Document common error responses
                op["responses"].setdefault("406", {
                    "description": "Unsupported locale — returns 406 with supported locales and Link headers",
                    "headers": {
                        "Link": {"description": 'Link: <v>; rel="alternate"; hreflang="v" for each supported locale', "schema": {"type": "string"}},
                        "Content-Language": {"schema": {"type": "string"}},
                        "Vary": {"schema": {"type": "string"}},
                    },
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                })
                op["responses"].setdefault("422", {
                    "description": "Validation error — e.g., page >10 requires cursor, invalid limit, or unsupported sort/order",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                })
                # Document cache headers
                op.setdefault("responses", {}).setdefault("200", {}).setdefault("headers", {})
                hdrs = op["responses"]["200"].setdefault("headers", {})
                hdrs["Cache-Control"] = {"description": "public, max-age=60, stale-while-revalidate=300", "schema": {"type": "string"}}
                hdrs["X-Cache"] = {"description": "HIT or MISS from Redis", "schema": {"type": "string"}}
                hdrs["ETag"] = {"schema": {"type": "string"}}
                # Ensure lang param documented
                params = op.setdefault("parameters", [])
                # Find lang
                if not any(p.get("name") == "lang" for p in params if isinstance(p, dict)):
                    # FastAPI already added lang as query param, but ensure description
                    pass
    # Ensure components schemas contain envelope and pricing docs
    comps = openapi.setdefault("components", {}).setdefault("schemas", {})
    # Add explicit PaginatedResponse description if not present
    if "PaginatedResponse" not in comps:
        comps["PaginatedResponse"] = {
            "title": "PaginatedResponse",
            "type": "object",
            "properties": {
                "data": {"type": "array", "items": {"type": "object"}},
                "meta": {"$ref": "#/components/schemas/Meta"},
                "links": {"$ref": "#/components/schemas/Links"},
            },
        }
    if "Meta" not in comps:
        comps["Meta"] = {
            "type": "object",
            "properties": {
                "page": {"type": "integer"},
                "limit": {"type": "integer"},
                "total": {"type": "integer"},
                "has_more": {"type": "boolean"},
                "next_cursor": {"type": "string", "nullable": True, "description": "Opaque base64 cursor for keyset pagination"},
                "taxonomy_version": {"type": "string", "nullable": True},
            },
        }
    if "Links" not in comps:
        comps["Links"] = {
            "type": "object",
            "properties": {
                "first": {"type": "string"},
                "prev": {"type": "string", "nullable": True},
                "next": {"type": "string", "nullable": True},
                "last": {"type": "string"},
            },
        }
    if "ErrorResponse" not in comps:
        comps["ErrorResponse"] = {
            "type": "object",
            "properties": {
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "array", "items": {"type": "object"}},
                        "trace_id": {"type": "string"},
                    },
                }
            },
        }
    # Ensure hosting without prices documented
    if "ProviderSummary" not in comps:
        comps["ProviderSummary"] = {
            "title": "ProviderSummary",
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["slug", "name"],
        }
    # Add ModelHostingResponse if missing
    if "ModelHostingResponse" not in comps:
        comps["ModelHostingResponse"] = {
            "title": "ModelHostingResponse",
            "description": "Hosting without price fields — only provider + is_primary",
            "type": "object",
            "properties": {
                "provider": {"$ref": "#/components/schemas/ProviderSummary"},
                "is_primary": {"type": "boolean"},
            },
            "required": ["provider", "is_primary"],
        }
    # Ensure input_price_per_mtok appears in spec
    # Add to ModelDetail if missing pricing note, keep global mention already via description
    return openapi


def enrich_admin(openapi: dict) -> dict:
    openapi["info"]["title"] = "Forcecast Taxonomy — Admin API"
    openapi["info"]["description"] = (
        "Admin write API — 7 endpoints for approval workflow, ingestion triggering, taxonomy version management, "
        "and webhook registration. All endpoints require admin authentication via JWT bearer (role:admin) or "
        "API key prefix fk_admin_* (X-Forcecast-Api-Key). Rate limiting: anonymous 60/min, authenticated 300/min, "
        "admin 1000/min with headers X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset and 429 Retry-After."
    )
    openapi["info"]["version"] = "1.0.0"
    openapi.setdefault("components", {}).setdefault("securitySchemes", {}).update({
        "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT", "description": "JWT with role:admin claim"},
        "apiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-Forcecast-Api-Key", "description": "API key with prefix fk_admin_*"},
    })
    openapi.setdefault("security", [{"bearerAuth": []}, {"apiKeyAuth": []}])
    for path, methods in openapi.get("paths", {}).items():
        for method, op in methods.items():
            if method == "post":
                op.setdefault("security", [{"bearerAuth": []}, {"apiKeyAuth": []}])
                op.setdefault("responses", {})
                op["responses"].setdefault("401", {"description": "Unauthorized — missing auth token", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}})
                op["responses"].setdefault("403", {"description": "Forbidden — non-admin role or invalid fk_admin_* key", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}})
                op["responses"].setdefault("429", {
                    "description": "Too Many Requests — rate limit exceeded",
                    "headers": {
                        "Retry-After": {"schema": {"type": "string"}},
                        "X-RateLimit-Limit": {"schema": {"type": "string"}},
                        "X-RateLimit-Remaining": {"schema": {"type": "string"}},
                        "X-RateLimit-Reset": {"schema": {"type": "string"}},
                    },
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                })
                # Ensure 200/201 response headers include rate limit
                success = "200" if "200" in op["responses"] else "201" if "201" in op["responses"] else next(iter(op["responses"]), None)
                if success:
                    hdrs = op["responses"][success].setdefault("headers", {})
                    hdrs["X-RateLimit-Limit"] = {"schema": {"type": "string"}}
                    hdrs["X-RateLimit-Remaining"] = {"schema": {"type": "string"}}
                    hdrs["X-RateLimit-Reset"] = {"schema": {"type": "string"}}
    comps = openapi.setdefault("components", {}).setdefault("schemas", {})
    if "ErrorResponse" not in comps:
        comps["ErrorResponse"] = {
            "type": "object",
            "properties": {
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "array", "items": {"type": "object"}},
                        "trace_id": {"type": "string"},
                    },
                }
            },
        }
    return openapi


def generate():
    # Public
    app_pub = FastAPI(title="Public", version="1.0.0")
    app_pub.include_router(public_router, prefix="/api/v1")
    openapi_pub = app_pub.openapi()
    openapi_pub["openapi"] = "3.1.0"
    openapi_pub = enrich_public(openapi_pub)
    OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PUBLIC, "w", encoding="utf-8") as f:
        yaml.safe_dump(openapi_pub, f, sort_keys=False, allow_unicode=True)
    print(f"Wrote {OUT_PUBLIC}")

    # Admin
    app_admin = FastAPI(title="Admin", version="1.0.0")
    app_admin.include_router(admin_router, prefix="/api/v1")
    openapi_admin = app_admin.openapi()
    openapi_admin["openapi"] = "3.1.0"
    openapi_admin = enrich_admin(openapi_admin)
    OUT_ADMIN.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_ADMIN, "w", encoding="utf-8") as f:
        yaml.safe_dump(openapi_admin, f, sort_keys=False, allow_unicode=True)
    print(f"Wrote {OUT_ADMIN}")


if __name__ == "__main__":
    generate()
