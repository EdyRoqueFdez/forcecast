"""Auth middleware — get_current_user, require_api_key, require_admin."""

import hashlib
import time
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.user import User
from app.auth.models.api_key import APIKey
from app.db.session import get_session
from app.auth.services import jwt as jwt_service
from app.auth.services.api_keys import check_rate_limit

# Redis accessor — patchable in tests
_redis_client: Any = None


def get_redis() -> Any:
    if _redis_client is not None:
        return _redis_client
    return {}


def set_redis(client: Any) -> None:
    global _redis_client
    _redis_client = client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _fetch_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    try:
        result = await db.execute(select(User).where(User.id == str(user_id)))  # type: ignore
        return result.scalars().first()  # type: ignore
    except Exception:
        return None


# ---------------------------------------------------------------------------
# get_current_user — JWT via cookie or Authorization Bearer
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Extract JWT from Authorization header or cookie, validate, return User."""
    token: str | None = None

    # Check Authorization header first
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth:
        scheme, param = get_authorization_scheme_param(auth)
        if scheme.lower() == "bearer" and param:
            token = param.strip()

    # Fallback to cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    redis = get_redis()
    try:
        payload = await jwt_service.verify_token(token, redis)
    except Exception as e:
        msg = str(e).lower()
        if "expired" in msg:
            raise HTTPException(status_code=401, detail="token expired")
        if "revoked" in msg:
            raise HTTPException(status_code=401, detail="token revoked")
        # try decode to distinguish expired
        try:
            jwt_service.decode_token(token)
        except Exception as de:
            if "expired" in str(de).lower():
                raise HTTPException(status_code=401, detail="token expired")
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing sub")

    user = await _fetch_user_by_id(db, str(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require admin role."""
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_val != "admin":
        raise HTTPException(status_code=403, detail="admin access required")
    return user


# ---------------------------------------------------------------------------
# require_api_key — X-Forcecast-Api-Key header
# ---------------------------------------------------------------------------
async def require_api_key(
    request: Request,
    db: AsyncSession = Depends(get_session),
    response: Response = None,  # type: ignore
) -> User:
    """Validate X-Forcecast-Api-Key header, check revocation, enforce rate limit, return User."""
    # header names are case-insensitive, Starlette normalizes to lower
    api_key: str | None = request.headers.get("x-forcecast-api-key")
    if not api_key:
        # also try case variations via raw headers
        api_key = request.headers.get("X-Forcecast-Api-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    # hash lookup
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    try:
        result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))  # type: ignore
        api_key_row = result.scalars().first()  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid API key") from e

    if not api_key_row:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if getattr(api_key_row, "revoked_at", None) is not None:
        raise HTTPException(status_code=401, detail="API key revoked")

    # Check expiration
    from datetime import datetime, timezone
    if getattr(api_key_row, "expires_at", None) is not None:
        if api_key_row.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="API key expired")

    # fetch associated user
    user = await _fetch_user_by_id(db, str(api_key_row.user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found for API key")

    # Rate limiting per key
    limit = getattr(api_key_row, "rate_limit_rpm", 60) or 60
    redis = get_redis()
    is_limited, remaining, retry_after = await check_rate_limit(redis, key_hash, int(limit))

    # Set rate limit headers if response available
    # We set on request.state for later middleware, and try to set directly if response passed
    # FastAPI dependencies can modify response headers via Response object if injected
    # Store for downstream
    request.state.api_key_id = str(api_key_row.id)
    request.state.api_key_scopes = getattr(api_key_row, "scopes", [])
    request.state.is_api_key = True
    request.state.rate_limit_limit = limit
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_retry_after = retry_after

    # If response object was provided, set headers directly
    if response is not None:
        try:
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["Retry-After"] = str(retry_after) if is_limited else "0"
            # also add standard variants
            response.headers["X-Rate-Limit-Limit"] = str(limit)
            response.headers["X-Rate-Limit-Remaining"] = str(remaining)
        except Exception:
            pass
    else:
        # Even without response, we can set headers via request.state and rely on middleware/response handling
        # For this implementation, we also try to inject headers via a response hook: store in request.state
        pass

    if is_limited:
        # Raise 429 with headers; headers will be included via exception headers
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-Rate-Limit-Limit": str(limit),
                "X-Rate-Limit-Remaining": str(remaining),
            },
        )

    # Update last_used_at
    api_key_row.last_used_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except Exception:
        await db.rollback()

    # Also set headers on successful path via exception-free: we can't directly set response headers without response obj,
    # so we attach to request.state and rely on caller to copy to response. However for httpx tests, headers must be on response.
    # To ensure headers appear, we will try to set them via a workaround: if the route returns a Response, the dependency's headers need to be propagated.
    # We handle this by storing in request.state and having the route copy headers.

    return user


# ---------------------------------------------------------------------------
# Public endpoint exemptions — no authentication required
# ---------------------------------------------------------------------------
PUBLIC_ENDPOINTS: list[str] = [
    "/health",
    "/api/v1/models",
    "/api/v1/categories",
    "/api/v1/providers",
    "/api/v1/locales",
    "/api/v1/modalities",
    "/api/v1/meta",
    "/.well-known/jwks.json",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/login",
    "/auth/callback",
    "/auth/error",
]

AUTH_EXEMPT_ENDPOINTS: list[str] = [
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/auth/logout",
    "/auth/callback",
    "/auth/error",
    "/.well-known/jwks.json",
]


def is_public_path(path: str, method: str = "GET") -> bool:  # noqa: ARG001
    """Return True if path is public (no auth required). Prefix-matched."""
    # Normalize path: strip trailing slash except root
    normalized = path.rstrip("/") if len(path) > 1 else path
    for endpoint in PUBLIC_ENDPOINTS:
        ep_norm = endpoint.rstrip("/") if len(endpoint) > 1 else endpoint
        if normalized == ep_norm or normalized.startswith(ep_norm + "/"):
            return True
        # also allow exact contains for query handling (path without query)
        if normalized.startswith(ep_norm):
            # guard against false positives like /api/v1/modelsExtra
            # need prefix + slash or exact
            # already handled slash case; also allow if endpoint is prefix and next char is '/' or end
            if len(normalized) == len(ep_norm) or normalized[len(ep_norm)] == "/":
                return True
    return False


def is_auth_exempt_path(path: str) -> bool:
    """Return True if path is exempt from require_admin (auth endpoints)."""
    normalized = path.rstrip("/") if len(path) > 1 else path
    for endpoint in AUTH_EXEMPT_ENDPOINTS:
        ep_norm = endpoint.rstrip("/") if len(endpoint) > 1 else endpoint
        if normalized == ep_norm or normalized.startswith(ep_norm + "/"):
            return True
    return False


# ---------------------------------------------------------------------------
# Middleware composability — dual auth (JWT OR API key)
# ---------------------------------------------------------------------------
async def get_current_user_or_api_key(
    request: Request,
    db: AsyncSession = Depends(get_session),
    response: Response = None,  # type: ignore
) -> User:
    """Attempt JWT first (header/cookie), fallback to API key. Raises 401 if neither succeeds."""
    # Check if API key header present — needed to decide fallback logic
    api_key_header = request.headers.get("x-forcecast-api-key") or request.headers.get("X-Forcecast-Api-Key")

    # Check if JWT token is present (header or cookie)
    jwt_token: str | None = None
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth:
        scheme, param = get_authorization_scheme_param(auth)
        if scheme.lower() == "bearer" and param:
            jwt_token = param.strip()
    if not jwt_token:
        jwt_token = request.cookies.get("access_token")

    # If JWT present, try JWT path first
    if jwt_token:
        try:
            # Re-use get_current_user logic but with current request/db without needing to re-parse
            # Call get_current_user which will re-extract token and validate
            return await get_current_user(request, db)
        except HTTPException as e:
            # If JWT was present but invalid/expired/revoked, do NOT silently fallback to API key if API key also present? 
            # Spec: endpoint accepts either; if JWT present and fails, fallback to API key if available
            if api_key_header:
                try:
                    return await require_api_key(request, db, response)
                except HTTPException:
                    # Prefer original JWT error if both fail? Raise JWT error
                    raise e
            raise e
    # No JWT — try API key
    if api_key_header:
        return await require_api_key(request, db, response)
    raise HTTPException(status_code=401, detail="Missing authentication token")


# Alias for task compliance: 4.3 expects require_api_key dependency with header X-Forcecast-Api-Key
__all__ = [
    "get_current_user",
    "require_admin",
    "require_api_key",
    "get_current_user_or_api_key",
    "get_redis",
    "set_redis",
    "PUBLIC_ENDPOINTS",
    "AUTH_EXEMPT_ENDPOINTS",
    "is_public_path",
    "is_auth_exempt_path",
]
