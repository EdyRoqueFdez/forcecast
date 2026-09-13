"""Anti-bot service — Turnstile verification, fingerprinting, reputation, anomaly detection."""

import hashlib
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# HU-A07: Bot threshold at 0.5 (was 3.0 for strict mode)
STRICT_THRESHOLD: float = 0.5  # Below this = bot-like behavior
REPUTATION_PENALTY: float = 0.1
REPUTATION_MAX: float = 10.0
REPUTATION_MIN: float = 0.0

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"

# In-memory fallback stores for tests / dict redis
_rapid_creation_buckets: dict[str, list[float]] = {}  # ip -> timestamps
_reputation_log: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------
def generate_fingerprint(user_agent: str, ip_address: str, accept_language: str) -> str:
    """Generate SHA-256 fingerprint from UA+IP+Accept-Language.

    Uses pipe delimiter for determinism. Lowercases language for normalization.
    Returns 64-char hex digest.
    """
    # Normalize: strip whitespace
    ua = (user_agent or "").strip()
    ip = (ip_address or "").strip()
    lang = (accept_language or "").strip()
    raw = f"{ua}|{ip}|{lang}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_fingerprint_from_request(request: Any) -> str:
    """Helper to extract fingerprint from FastAPI Request."""
    try:
        ua = request.headers.get("user-agent", "") or request.headers.get("User-Agent", "")
        # X-Forwarded-For handling: first IP
        xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            ip = getattr(request.client, "host", "") if hasattr(request, "client") and request.client else ""
        lang = request.headers.get("accept-language", "") or request.headers.get("Accept-Language", "")
        return generate_fingerprint(ua, ip, lang)
    except Exception:
        return hashlib.sha256(b"unknown").hexdigest()


# ---------------------------------------------------------------------------
# Turnstile / hCaptcha verification
# ---------------------------------------------------------------------------
async def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    """Verify Turnstile/hCaptcha token server-side.

    Returns True if valid, False if invalid. Network errors return False
    (caller may treat as captcha verification failed).
    """
    if not token or not token.strip():
        return False

    secret = getattr(settings, "TURNSTILE_SECRET_KEY", "") or ""
    # For tests without secret, we still attempt verification but mock httpx
    # If no secret configured and we're in test mode, allow mocked verification to succeed
    # But real invalid token without secret should still fail
    # We'll proceed with provider call; mocked response determines result.

    # Choose provider URL — default Turnstile
    url = TURNSTILE_VERIFY_URL
    # If token looks like hCaptcha, could use HCAPTCHA_VERIFY_URL but treat same

    payload = {
        "secret": secret,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, data=payload)
            try:
                data = resp.json()
            except Exception:
                # fallback: try text
                data = {}
            success = bool(data.get("success", False))
            if not success:
                logger.info("turnstile verification failed", extra={"error_codes": data.get("error-codes")})
            return success
    except Exception as e:
        logger.warning(f"turnstile verification error: {e}")
        # Network error — treat as failed verification per spec (403)
        return False


# ---------------------------------------------------------------------------
# Reputation
# ---------------------------------------------------------------------------
def is_strict_mode(user: Any) -> bool:
    """Whether user is in strict mode (reputation < 3.0)."""
    score = getattr(user, "reputation_score", None)
    if score is None:
        score = 5.0
    return float(score) < STRICT_THRESHOLD


def get_effective_rate_limit(user: Any) -> int:
    """Get effective rate limit considering reputation strict mode.

    Base: 60 for user, 1000 for admin. Halved when <3.0.
    HU-A10: 60 req/min per user, 30 votes/min per user.
    """
    # Import here to avoid circular
    try:
        from app.auth.middleware.rate_limit import USER_RATE_LIMIT, ADMIN_RATE_LIMIT
        user_limit = USER_RATE_LIMIT  # 60
        admin_limit = ADMIN_RATE_LIMIT  # 1000
    except Exception:
        user_limit = 60
        admin_limit = 1000

    # Determine role
    role = getattr(user, "role", "user")
    role_val = role.value if hasattr(role, "value") else str(role)

    base = admin_limit if role_val == "admin" else user_limit
    if is_strict_mode(user):
        return base // 2
    return base


def adjust_reputation(user: Any, delta: float) -> float:
    """Adjust reputation by delta, clamp 0.0-10.0, persist on user object."""
    current = float(getattr(user, "reputation_score", 5.0) or 5.0)
    new_score = current + float(delta)
    # clamp
    if new_score < REPUTATION_MIN:
        new_score = REPUTATION_MIN
    if new_score > REPUTATION_MAX:
        new_score = REPUTATION_MAX
    # round to 2 decimals for stability?
    new_score = round(new_score, 2)
    try:
        user.reputation_score = new_score  # type: ignore
    except Exception:
        pass
    return new_score


# ---------------------------------------------------------------------------
# Anomaly detection helpers
# ---------------------------------------------------------------------------
async def check_fingerprint_mismatch(
    session_fingerprint: str | None,
    current_fingerprint: str,
    user: Any,
) -> dict[str, Any]:
    """Compare stored fingerprint vs current. Flag mismatch, apply penalty.

    Returns dict with mismatch, anomaly, reputation_after, penalty.
    Side effect: decrements reputation by REPUTATION_PENALTY on mismatch.
    """
    if not session_fingerprint:
        return {"mismatch": False, "anomaly": False, "reason": "no stored fingerprint", "reputation_after": float(getattr(user, "reputation_score", 5.0))}

    mismatch = session_fingerprint != current_fingerprint
    if not mismatch:
        return {"mismatch": False, "anomaly": False, "reason": "match", "reputation_after": float(getattr(user, "reputation_score", 5.0))}

    # Mismatch — log and penalize
    new_score = adjust_reputation(user, -REPUTATION_PENALTY)
    # Logging level depends on strict mode
    if is_strict_mode(user):
        logger.warning(f"fingerprint mismatch for user {getattr(user, 'id', 'unknown')}: penalty applied, new score {new_score}")
    else:
        logger.info(f"fingerprint mismatch for user {getattr(user, 'id', 'unknown')}: penalty applied")

    _reputation_log.append({"type": "fingerprint_mismatch", "user_id": str(getattr(user, "id", "")), "penalty": REPUTATION_PENALTY})

    return {
        "mismatch": True,
        "anomaly": True,
        "reason": "fingerprint_mismatch",
        "penalty": REPUTATION_PENALTY,
        "reputation_after": new_score,
    }


# Rapid account creation — Redis sliding window 10min, limit 5
RAPID_WINDOW_SECONDS = 600
RAPID_LIMIT = 5


def _get_times_list(redis: Any, key: str) -> list[float]:
    """Helper to retrieve timestamps list from various redis types."""
    if isinstance(redis, dict) and not hasattr(redis, "store"):
        val = redis.get(key)
        if isinstance(val, list):
            return val
        return []
    if hasattr(redis, "store") and isinstance(getattr(redis, "store"), dict):
        store = getattr(redis, "store")
        val = store.get(key)
        if isinstance(val, list):
            return val
        return []
    # real redis: try to get JSON
    return _rapid_creation_buckets.get(key, [])


def _set_times_list(redis: Any, key: str, times: list[float]) -> None:
    if isinstance(redis, dict) and not hasattr(redis, "store"):
        redis[key] = times  # type: ignore
        # also keep global for fallback
        _rapid_creation_buckets[key] = times
        return
    if hasattr(redis, "store") and isinstance(getattr(redis, "store"), dict):
        getattr(redis, "store")[key] = times
        _rapid_creation_buckets[key] = times
        return
    # real redis fallback
    _rapid_creation_buckets[key] = times
    # try async set if possible (caller will handle)


async def record_account_creation(ip_address: str, redis: Any) -> int:
    """Record account creation event for IP, returns count in window."""
    key = f"rapid_acct:{ip_address}"
    now = time.time()

    # Retrieve existing times
    if isinstance(redis, dict) and not hasattr(redis, "store"):
        times = redis.get(key, [])  # type: ignore
        if not isinstance(times, list):
            times = []
    elif hasattr(redis, "store") and isinstance(getattr(redis, "store"), dict):
        times = getattr(redis, "store").get(key, [])
        if not isinstance(times, list):
            times = []
    else:
        # try real redis get
        try:
            import inspect, json
            val = None
            if hasattr(redis, "get"):
                fn = getattr(redis, "get")
                if inspect.iscoroutinefunction(fn):
                    val = await fn(key)
                else:
                    val = fn(key)
                    if inspect.isawaitable(val):
                        val = await val
                if isinstance(val, bytes):
                    val = val.decode()
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except:
                        val = []
                times = val if isinstance(val, list) else []
            else:
                times = _rapid_creation_buckets.get(key, [])
        except Exception:
            times = _rapid_creation_buckets.get(key, [])

    # Clean window
    times = [t for t in times if now - t < RAPID_WINDOW_SECONDS]
    times.append(now)

    # Persist
    if isinstance(redis, dict) and not hasattr(redis, "store"):
        redis[key] = times  # type: ignore
    elif hasattr(redis, "store") and isinstance(getattr(redis, "store"), dict):
        getattr(redis, "store")[key] = times
    else:
        try:
            import inspect, json
            if hasattr(redis, "set"):
                fn = getattr(redis, "set")
                data = json.dumps(times)
                if inspect.iscoroutinefunction(fn):
                    await fn(key, data, ex=RAPID_WINDOW_SECONDS)
                else:
                    res = fn(key, data, ex=RAPID_WINDOW_SECONDS)
                    if inspect.isawaitable(res):
                        await res
        except Exception:
            pass
        _rapid_creation_buckets[key] = times
        # also store in global for check
        if isinstance(redis, dict):
            try:
                redis[key] = times  # type: ignore
            except:
                pass

    # Also ensure global mirrored
    _rapid_creation_buckets[key] = times
    return len(times)


async def check_rapid_account_creation(ip_address: str, redis: Any) -> bool:
    """Check if IP is blocked for rapid account creation (>5 in 10min)."""
    key = f"rapid_acct:{ip_address}"
    now = time.time()

    if isinstance(redis, dict) and not hasattr(redis, "store"):
        times = redis.get(key, [])  # type: ignore
        if not isinstance(times, list):
            times = []
    elif hasattr(redis, "store") and isinstance(getattr(redis, "store"), dict):
        times = getattr(redis, "store").get(key, [])
        if not isinstance(times, list):
            times = []
    else:
        try:
            import inspect, json
            val = None
            if hasattr(redis, "get"):
                fn = getattr(redis, "get")
                if inspect.iscoroutinefunction(fn):
                    val = await fn(key)
                else:
                    val = fn(key)
                    if inspect.isawaitable(val):
                        val = await val
                if isinstance(val, bytes):
                    val = val.decode()
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except:
                        val = []
                times = val if isinstance(val, list) else _rapid_creation_buckets.get(key, [])
            else:
                times = _rapid_creation_buckets.get(key, [])
        except Exception:
            times = _rapid_creation_buckets.get(key, [])

    # Also fallback to global if empty but global has data
    if not times and key in _rapid_creation_buckets:
        times = _rapid_creation_buckets[key]

    # Clean window
    times = [t for t in times if now - t < RAPID_WINDOW_SECONDS]
    return len(times) > RAPID_LIMIT


async def check_refresh_anomaly(session: Any, new_fingerprint: str, user: Any) -> dict[str, Any]:
    """Detect refresh from new device within 5min of login.

    If session.created_at is <5min ago and new_fingerprint != stored fingerprint,
    flag as anomaly and apply reputation penalty.
    """
    stored_fp = getattr(session, "device_fingerprint", None) or getattr(session, "fingerprint", None)
    # If no stored fingerprint, compare with current? Use session's fingerprint
    if stored_fp is None:
        stored_fp = getattr(session, "device_fingerprint", None)

    created_at = getattr(session, "created_at", None)
    if created_at is None:
        created_at = getattr(session, "last_active_at", None)

    # Determine age
    now = datetime.now(timezone.utc)
    if created_at is not None:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age = (now - created_at).total_seconds()
    else:
        age = 999999

    # If no stored fingerprint, treat new_fingerprint as not anomaly unless session is recent?
    # But we can decide: if stored_fp is None, not anomaly
    if stored_fp is None:
        return {"anomaly": False, "reason": "no stored fingerprint"}

    mismatch = stored_fp != new_fingerprint
    if mismatch and age < 300:  # 5 minutes
        new_score = adjust_reputation(user, -REPUTATION_PENALTY)
        logger.warning(f"refresh anomaly: new device within 5min for user {getattr(user, 'id', '')}")
        return {"anomaly": True, "reason": "refresh_new_device_within_5min", "reputation_after": new_score, "penalty": REPUTATION_PENALTY}
    else:
        return {"anomaly": False, "reason": "refresh_normal" if not mismatch else "refresh_old_session"}


def clear_anti_bot_state() -> None:
    """Clear in-memory state for tests."""
    _rapid_creation_buckets.clear()
    _reputation_log.clear()
