"""Admin auth + rate limiting dependencies for taxonomy."""
from __future__ import annotations

import hashlib
import time

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.api_key import APIKey
from app.auth.models.user import User
from app.auth.services.jwt import decode_token
from app.db.session import get_session

# In-memory sliding window for rate limiting (per key = ip or user_id)
_buckets: dict[str, list[float]] = {}

# Limits
ANON_LIMIT = 60
AUTH_LIMIT = 300
ADMIN_LIMIT = 1000


def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and hasattr(request.client, "host"):
        return request.client.host
    return "unknown"


async def _fetch_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    try:
        result = await db.execute(select(User).where(User.id == str(user_id)))
        return result.scalars().first()
    except Exception:
        return None


async def require_admin(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Require admin: JWT role:admin OR API key fk_admin_* prefix."""
    # Try JWT first
    token: str | None = None
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth:
        scheme, param = get_authorization_scheme_param(auth)
        if scheme.lower() == "bearer" and param:
            token = param.strip()

    if token:
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            role = payload.get("role", "")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: missing sub")
            user = await _fetch_user_by_id(db, str(user_id))
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
            # Also check payload role
            if role_val != "admin" and str(role) != "admin":
                raise HTTPException(status_code=403, detail="admin access required")
            # Set rate limit headers later via RateLimiter? Also set here for anon? We'll set basic headers
            return user
        except HTTPException:
            raise
        except Exception as e:
            msg = str(e).lower()
            if "expired" in msg:
                raise HTTPException(status_code=401, detail="token expired")
            # Fall through to try API key if JWT invalid
            # But if token was present and invalid, we should not silently fallback? Spec says either, so try api key fallback if provided
            api_key_header = request.headers.get("x-forcecast-api-key") or request.headers.get("X-Forcecast-Api-Key")
            if not api_key_header:
                raise HTTPException(status_code=401, detail="Invalid token")

    # Try API key
    api_key: str | None = request.headers.get("x-forcecast-api-key") or request.headers.get("X-Forcecast-Api-Key")
    if api_key:
        if not api_key.startswith("fk_admin_"):
            # Spec requires prefix fk_admin_* for admin; non-prefix -> 403 or 401
            # If prefix is fk_ but not fk_admin_, treat as forbidden (non-admin key)
            raise HTTPException(status_code=403, detail="admin access required")
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        try:
            result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
            row = result.scalars().first()
        except Exception:
            row = None
        if row:
            if getattr(row, "revoked_at", None) is not None:
                raise HTTPException(status_code=401, detail="API key revoked")
            user = await _fetch_user_by_id(db, str(row.user_id))
            if not user:
                raise HTTPException(status_code=401, detail="User not found for API key")
            role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
            if role_val != "admin":
                raise HTTPException(status_code=403, detail="admin access required")
            return user
        else:
            # For tests without DB row but prefix valid, we allow fallback: require JWT user? but we already tried JWT
            # If no DB row but key starts with fk_admin_, we can't verify — treat as 401 unless we synthesize
            # To allow tests that use synthetic fk_admin_ keys without DB, we can require that if no row, we still check prefix and allow if token missing?
            # For this project, tests that use raw fk_admin_ key DO create DB row, so this path should have found row. If not found, 401
            raise HTTPException(status_code=401, detail="Invalid API key")
    # No auth
    raise HTTPException(status_code=401, detail="Missing authentication token")


class RateLimiter:
    """Simple sliding window rate limiter as FastAPI dependency."""

    def __init__(self, requests_per_minute: int = 60, window: int = 60):
        self.limit = requests_per_minute
        self.window = window

    async def __call__(self, request: Request, response: Response):
        # Key: per IP or per user if authenticated already? Use IP for simplicity + user id if available
        ip = _get_client_ip(request)
        # Try to get user id from auth header if present (we don't have user here, so use IP)
        key = f"rl:{ip}:{self.limit}"
        # Use global buckets
        now = time.time()
        times = _buckets.get(key, [])
        # clean
        times = [t for t in times if now - t < self.window]
        if len(times) >= self.limit:
            remaining = 0
            oldest = times[0] if times else now
            retry_after = int(self.window - (now - oldest))
            if retry_after <= 0:
                retry_after = self.window
            reset_ts = int(now + retry_after)
            # set headers even on 429 via exception headers, but also try to set on response
            try:
                response.headers["X-RateLimit-Limit"] = str(self.limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(reset_ts)
                response.headers["X-Rate-Limit-Limit"] = str(self.limit)
                response.headers["X-Rate-Limit-Remaining"] = "0"
                response.headers["Retry-After"] = str(retry_after)
            except Exception:
                pass
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_ts),
                    "X-Rate-Limit-Limit": str(self.limit),
                    "X-Rate-Limit-Remaining": "0",
                },
            )
        # allow
        times.append(now)
        _buckets[key] = times
        remaining = self.limit - len(times)
        reset_ts = int(now + self.window - (now - times[0]) if times else self.window)
        try:
            response.headers["X-RateLimit-Limit"] = str(self.limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_ts)
            response.headers["X-Rate-Limit-Limit"] = str(self.limit)
            response.headers["X-Rate-Limit-Remaining"] = str(remaining)
        except Exception:
            pass
        # Also store on request.state for visibility
        try:
            request.state.rate_limit_limit = self.limit
            request.state.rate_limit_remaining = remaining
        except Exception:
            pass


def clear_rate_limit_state():
    _buckets.clear()


# Alias for admin rate limiter (1000/min)
admin_rate_limiter = RateLimiter(requests_per_minute=ADMIN_LIMIT)
