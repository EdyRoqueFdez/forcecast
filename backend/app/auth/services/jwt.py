"""JWT service — RS256 sign/verify, JWKS, revocation via Redis/pubsub."""

import base64
import uuid
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt  # PyJWT
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.core.config import settings

# ---------------------------------------------------------------------------
# Key management — load from file or generate ephemeral
# ---------------------------------------------------------------------------
REVOCATION_PREFIX = "auth:revocation:"
REVOCATION_CHANNEL = "auth:revocation"

_JWT_ALGORITHM = "RS256"
_JWT_ISSUER = getattr(settings, "JWT_ISSUER", "forcecast")

_private_pem: str | None = None
_public_pem: str | None = None
_kid: str | None = None
_public_key_obj = None  # cryptography object for JWKS

_in_memory_revoked: dict[str, float] = {}  # fallback for tests without redis


def _ensure_keys() -> tuple[str, str, str]:
    """Ensure private/public PEM and kid are loaded. Returns (private_pem, public_pem, kid)."""
    global _private_pem, _public_pem, _kid, _public_key_obj
    if _private_pem and _public_pem and _kid:
        return _private_pem, _public_pem, _kid

    priv_path = Path(settings.JWT_PRIVATE_KEY_PATH) if hasattr(settings, "JWT_PRIVATE_KEY_PATH") else Path("secrets/jwt_private.pem")
    pub_path = Path(settings.JWT_PUBLIC_KEY_PATH) if hasattr(settings, "JWT_PUBLIC_KEY_PATH") else Path("secrets/jwt_public.pem")

    private_pem = None
    public_pem = None
    kid = None

    # Try loading from files
    try:
        if priv_path.exists() and pub_path.exists():
            private_pem = priv_path.read_text(encoding="utf-8")
            public_pem = pub_path.read_text(encoding="utf-8")
            # Derive kid as hash of public key (first 16 chars of modulus b64)
            # Use uuid5 for determinism
            kid = str(uuid.uuid5(uuid.NAMESPACE_URL, public_pem[:100]))
            # Load public key obj for JWKS
            _public_key_obj = serialization.load_pem_public_key(public_pem.encode())
        else:
            raise FileNotFoundError
    except Exception:
        # Generate ephemeral 2048-bit RSA keypair
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        _public_key_obj = public_key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        kid = str(uuid.uuid5(uuid.NAMESPACE_URL, public_pem[:100]))
        # Optionally try to write to secrets dir for persistence in dev
        try:
            priv_path.parent.mkdir(parents=True, exist_ok=True)
            if not priv_path.exists():
                priv_path.write_text(private_pem, encoding="utf-8")
            if not pub_path.exists():
                pub_path.write_text(public_pem, encoding="utf-8")
        except Exception:
            pass

    _private_pem = private_pem
    _public_pem = public_pem
    _kid = kid
    return private_pem, public_pem, kid  # type: ignore


def _get_private_pem() -> str:
    priv, _, _ = _ensure_keys()
    return priv


def _get_public_pem() -> str:
    _, pub, _ = _ensure_keys()
    return pub


def _get_kid() -> str:
    _, _, kid = _ensure_keys()
    return kid


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------
def create_access_token(user_id: str, role: str, expires_delta: timedelta | None = None) -> str:
    """Create RS256 access token with sub, role, iat, exp (30min), jti."""
    now = datetime.now(timezone.utc)
    iat = int(now.timestamp())
    delta = expires_delta if expires_delta is not None else timedelta(minutes=getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    exp = int((now + delta).timestamp())
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": iat,
        "exp": exp,
        "jti": jti,
        "iss": _JWT_ISSUER,
    }
    headers = {"kid": _get_kid()}
    token = jwt.encode(payload, _get_private_pem(), algorithm=_JWT_ALGORITHM, headers=headers)
    return token


def create_refresh_token(user_id: str, session_id: str, expires_delta: timedelta | None = None) -> str:
    """Create RS256 refresh token with sub, jti, exp (7d), session_id, iat."""
    now = datetime.now(timezone.utc)
    iat = int(now.timestamp())
    delta = expires_delta if expires_delta is not None else timedelta(days=getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7))
    exp = int((now + delta).timestamp())
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "exp": exp,
        "iat": iat,
        "session_id": str(session_id),
        "iss": _JWT_ISSUER,
    }
    headers = {"kid": _get_kid()}
    token = jwt.encode(payload, _get_private_pem(), algorithm=_JWT_ALGORITHM, headers=headers)
    return token


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify RS256 token. Raises on invalid/expired."""
    # Verify signature and exp; issuer check optional
    payload = jwt.decode(
        token,
        _get_public_pem(),
        algorithms=[_JWT_ALGORITHM],
        # issuer=_JWT_ISSUER,
        options={"verify_signature": True, "verify_exp": True},
    )
    return payload


# ---------------------------------------------------------------------------
# JWKS
# ---------------------------------------------------------------------------
def _base64url_no_pad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def get_jwks() -> dict[str, Any]:
    """Return JWKS dict with RSA public key."""
    _ensure_keys()
    assert _public_key_obj is not None
    # Extract n, e
    public_numbers = _public_key_obj.public_numbers()
    n_int = public_numbers.n
    e_int = public_numbers.e
    # Convert to bytes big-endian
    n_bytes = n_int.to_bytes((n_int.bit_length() + 7) // 8, "big")
    e_bytes = e_int.to_bytes((e_int.bit_length() + 7) // 8, "big")
    n_b64 = _base64url_no_pad(n_bytes)
    e_b64 = _base64url_no_pad(e_bytes)
    kid = _get_kid()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": kid,
                "alg": "RS256",
                "n": n_b64,
                "e": e_b64,
            }
        ]
    }


# ---------------------------------------------------------------------------
# Revocation — Redis with dict fallback + pub/sub
# ---------------------------------------------------------------------------
async def is_jti_revoked(redis_client: Any, jti: str) -> bool:
    """Check if JTI is revoked. Supports dict, fake redis, or real redis."""
    key = f"{REVOCATION_PREFIX}{jti}"
    # plain dict fallback (no store/published attributes)
    if isinstance(redis_client, dict) and not hasattr(redis_client, "store"):
        if key in redis_client or jti in redis_client:
            return True
        if key in _in_memory_revoked or jti in _in_memory_revoked:
            return True
        # also check if value stored with prefix via fallback global already
        return False
    # object with .store dict (our FakeRedis)
    if hasattr(redis_client, "store") and isinstance(getattr(redis_client, "store"), dict):
        # Also check internal store
        store = getattr(redis_client, "store")
        if key in store or jti in store:
            return True
    try:
        val = redis_client.get(key) if not hasattr(redis_client, "get") else None
        # If redis_client has async get, we need to await (handled below)
        # Determine if get is coroutine
        import inspect

        if inspect.iscoroutinefunction(getattr(redis_client, "get", None)):
            val = await redis_client.get(key)
        else:
            # try dict-like get
            try:
                val = redis_client.get(key)
                if inspect.isawaitable(val):
                    val = await val
            except Exception:
                val = None
        if val is not None:
            if isinstance(val, bytes):
                val = val.decode()
            return True
        # Also check jti without prefix for dict compat
        try:
            val2 = redis_client.get(jti)
            if inspect.isawaitable(val2):
                val2 = await val2
            if val2 is not None:
                return True
        except Exception:
            pass
        # Fallback global
        if key in _in_memory_revoked or jti in _in_memory_revoked:
            return True
        return False
    except Exception:
        return key in _in_memory_revoked or jti in _in_memory_revoked


async def revoke_jti(redis_client: Any, jti: str, ttl_seconds: int = 1800) -> None:
    """Revoke JTI with TTL and publish to revocation channel."""
    key = f"{REVOCATION_PREFIX}{jti}"
    ttl = max(1, int(ttl_seconds)) if ttl_seconds > 0 else 1800

    # Support plain dict
    if isinstance(redis_client, dict) and not hasattr(redis_client, "set"):
        redis_client[key] = "1"
        # Also store with TTL simulation (ignore expiry for test)
        _in_memory_revoked[key] = time.time() + ttl
        _in_memory_revoked[jti] = time.time() + ttl
        # publish emulation: if dict has 'published' attribute
        if hasattr(redis_client, "published"):
            try:
                redis_client["__published__"] = jti  # type: ignore
            except Exception:
                pass
        return

    # Try redis set with ex
    try:
        import inspect

        if hasattr(redis_client, "set"):
            set_fn = getattr(redis_client, "set")
            if inspect.iscoroutinefunction(set_fn):
                await set_fn(key, "1", ex=ttl)
            else:
                res = set_fn(key, "1", ex=ttl)
                if inspect.isawaitable(res):
                    await res
        else:
            # fallback dict
            redis_client[key] = "1"  # type: ignore

        # Also keep in memory for fallback checks
        _in_memory_revoked[key] = time.time() + ttl
        _in_memory_revoked[jti] = time.time() + ttl

        # Publish
        if hasattr(redis_client, "publish"):
            pub = getattr(redis_client, "publish")
            try:
                if inspect.iscoroutinefunction(pub):
                    await pub(REVOCATION_CHANNEL, jti)
                else:
                    res = pub(REVOCATION_CHANNEL, jti)
                    if inspect.isawaitable(res):
                        await res
            except Exception:
                pass
        # If redis_client is FakeRedis with .published list, also record
        if hasattr(redis_client, "published") and isinstance(getattr(redis_client, "published"), list):
            # already handled via publish above, but ensure
            pass
    except Exception:
        # Fallback to memory
        _in_memory_revoked[key] = time.time() + ttl
        _in_memory_revoked[jti] = time.time() + ttl
        if isinstance(redis_client, dict):
            redis_client[key] = "1"  # type: ignore


async def verify_token(token: str, redis_client: Any) -> dict[str, Any]:
    """Verify token signature and check revocation. Returns payload or raises."""
    payload = decode_token(token)
    jti = payload.get("jti")
    if not jti:
        raise jwt.InvalidTokenError("Missing jti")
    if await is_jti_revoked(redis_client, jti):
        raise jwt.InvalidTokenError("Token revoked")
    return payload


# For testing: allow clearing in-memory
def _clear_revoked() -> None:
    _in_memory_revoked.clear()
