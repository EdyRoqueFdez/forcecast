"""Rate limiter middleware — Redis sliding window, tiers, 429 with Retry-After."""

import time
import logging
from typing import Any

from fastapi import HTTPException, Request

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tier limits from config with fallbacks
LOGIN_IP_LIMIT: int = getattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 10)
REGISTER_IP_LIMIT: int = getattr(settings, "RATE_LIMIT_REGISTER_PER_MINUTE", 5)
USER_RATE_LIMIT: int = getattr(settings, "RATE_LIMIT_USER_PER_MINUTE", 300)
ADMIN_RATE_LIMIT: int = getattr(settings, "RATE_LIMIT_ADMIN_PER_MINUTE", 1000)

# In-memory fallback for tests (when redis is dict, we use redis dict directly)
# But also keep global for real redis fallback
_memory_buckets: dict[str, list[float]] = {}


async def check_rate_limit(redis: Any, key: str, limit: int, window: int = 60) -> tuple[bool, int, int]:
    """Sliding window rate limit check.

    Returns (is_limited, remaining, retry_after_seconds).
    Supports dict, FakeRedis (with .store), and real redis (async get/set).
    """
    now = time.time()
    bucket_key = key

    # Helper to get times list
    times: list[float] | None = None

    # Case 1: plain dict (tests use {} )
    if isinstance(redis, dict) and not hasattr(redis, "store"):
        val = redis.get(bucket_key)
        if isinstance(val, list):
            times = val
        elif val is None:
            times = []
        else:
            # If val is int from old fixed window, convert to list approximation
            if isinstance(val, int):
                # approximate: spread count over last window? simple: not limited handling
                times = [now - 1] * int(val)  # approximate
            else:
                times = []

        # clean window
        times = [t for t in times if now - t < window]

        if len(times) < limit:
            times.append(now)
            redis[bucket_key] = times  # type: ignore
            _memory_buckets[bucket_key] = times
            remaining = limit - len(times)
            # retry_after based on oldest entry expiry
            if times:
                oldest = times[0]
                retry_after = int(window - (now - oldest))
                if retry_after <= 0:
                    retry_after = window
            else:
                retry_after = window
            return False, remaining, max(1, retry_after)
        else:
            oldest = times[0] if times else now
            retry_after = int(window - (now - oldest))
            if retry_after <= 0:
                retry_after = window
            # still store cleaned times (don't add new)
            redis[bucket_key] = times  # type: ignore
            return True, 0, max(1, retry_after)

    # Case 2: FakeRedis with .store dict
    if hasattr(redis, "store") and isinstance(getattr(redis, "store"), dict):
        store = getattr(redis, "store")
        val = store.get(bucket_key)
        if isinstance(val, list):
            times = val
        elif val is None:
            times = []
        else:
            times = []
        times = [t for t in times if now - t < window]
        if len(times) < limit:
            times.append(now)
            store[bucket_key] = times
            _memory_buckets[bucket_key] = times
            remaining = limit - len(times)
            retry_after = int(window - (now - times[0])) if times else window
            return False, remaining, max(1, retry_after)
        else:
            retry_after = int(window - (now - times[0])) if times else window
            store[bucket_key] = times
            return True, 0, max(1, retry_after)

    # Case 3: real redis async
    try:
        import inspect
        import json

        val = None
        if hasattr(redis, "get"):
            get_fn = getattr(redis, "get")
            if inspect.iscoroutinefunction(get_fn):
                val = await get_fn(bucket_key)
            else:
                val = get_fn(bucket_key)
                if inspect.isawaitable(val):
                    val = await val
            # parse val
            if val is None:
                times = []
            elif isinstance(val, bytes):
                try:
                    times = json.loads(val.decode())
                except:
                    times = []
            elif isinstance(val, str):
                try:
                    times = json.loads(val)
                except:
                    times = []
            elif isinstance(val, list):
                times = val
            else:
                times = []
        else:
            times = _memory_buckets.get(bucket_key, [])

        if times is None:
            times = []
        # ensure list of floats
        if not isinstance(times, list):
            times = []
        times = [float(t) for t in times if isinstance(t, (int, float)) and now - float(t) < window]

        if len(times) < limit:
            times.append(now)
            if hasattr(redis, "set"):
                set_fn = getattr(redis, "set")
                data = json.dumps(times)
                if inspect.iscoroutinefunction(set_fn):
                    await set_fn(bucket_key, data, ex=window)
                else:
                    res = set_fn(bucket_key, data, ex=window)
                    if inspect.isawaitable(res):
                        await res
            _memory_buckets[bucket_key] = times
            remaining = limit - len(times)
            retry_after = int(window - (now - times[0])) if times else window
            return False, remaining, max(1, retry_after)
        else:
            retry_after = int(window - (now - times[0])) if times else window
            # persist cleaned
            if hasattr(redis, "set"):
                set_fn = getattr(redis, "set")
                data = json.dumps(times)
                try:
                    if inspect.iscoroutinefunction(set_fn):
                        await set_fn(bucket_key, data, ex=window)
                    else:
                        res = set_fn(bucket_key, data, ex=window)
                        if inspect.isawaitable(res):
                            await res
                except:
                    pass
            _memory_buckets[bucket_key] = times
            return True, 0, max(1, retry_after)
    except Exception as e:
        logger.warning(f"rate limit redis error: {e}, fallback to memory")
        # fallback to memory
        times = _memory_buckets.get(bucket_key, [])
        times = [t for t in times if now - t < window]
        if len(times) < limit:
            times.append(now)
            _memory_buckets[bucket_key] = times
            remaining = limit - len(times)
            retry_after = int(window - (now - times[0])) if times else window
            return False, remaining, max(1, retry_after)
        else:
            retry_after = int(window - (now - times[0])) if times else window
            _memory_buckets[bucket_key] = times
            return True, 0, max(1, retry_after)


async def enforce_ip_rate_limit(request: Request, redis: Any, endpoint: str = "login") -> None:
    """Enforce per-IP rate limit for given endpoint. Raises 429 if exceeded."""
    # Extract IP
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        ip = xff.split(",")[0].strip()
    else:
        ip = getattr(request.client, "host", "unknown") if hasattr(request, "client") and request.client else "unknown"

    if endpoint == "login":
        limit = LOGIN_IP_LIMIT
        key = f"login:{ip}"
    elif endpoint == "register":
        limit = REGISTER_IP_LIMIT
        key = f"register:{ip}"
    else:
        limit = LOGIN_IP_LIMIT
        key = f"{endpoint}:{ip}"

    is_limited, remaining, retry_after = await check_rate_limit(redis, key, limit, window=60)
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail=f"Too many {endpoint} attempts from this IP" if endpoint in ("login", "register") else "Rate limit exceeded",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-Rate-Limit-Limit": str(limit),
                "X-Rate-Limit-Remaining": str(remaining),
            },
        )
    # Optionally set headers on request.state for downstream
    try:
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = limit
    except:
        pass


async def enforce_user_rate_limit(request: Request, redis: Any, user: Any) -> None:
    """Enforce per-user rate limit (300 user / 1000 admin, halved if <3.0). Raises 429."""
    from app.auth.services.anti_bot import get_effective_rate_limit

    effective = get_effective_rate_limit(user)
    uid = str(getattr(user, "id", "unknown"))
    key = f"user:{uid}"
    is_limited, remaining, retry_after = await check_rate_limit(redis, key, effective, window=60)
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(effective),
                "X-RateLimit-Remaining": str(remaining),
                "X-Rate-Limit-Limit": str(effective),
                "X-Rate-Limit-Remaining": str(remaining),
            },
        )
    try:
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = effective
    except:
        pass


def clear_rate_limit_state() -> None:
    """Clear in-memory buckets for tests."""
    _memory_buckets.clear()
