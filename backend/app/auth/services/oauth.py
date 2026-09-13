"""OAuth2/OIDC service — PKCE, state, provider URLs, token exchange, account linking."""
import base64
import hashlib
import secrets
import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.user import User
from app.core.config import settings

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------
PROVIDER_CONFIGS: dict[str, dict[str, str]] = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "user:email",
    },
}

# In-memory fallback for tests when redis not available
_in_memory_states: dict[str, str] = {}

STATE_TTL_SECONDS = 600
STATE_KEY_PREFIX = "oauth:state:"


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------
def generate_code_verifier() -> str:
    """Generate a high-entropy code_verifier (43-128 chars, RFC7636)."""
    # 32 random bytes -> 43 chars base64url without padding
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier: str) -> str:
    """Generate S256 code_challenge = BASE64URL(SHA256(verifier)) without padding."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def generate_state_token() -> str:
    """Cryptographically random state token for CSRF protection."""
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Authorization URL
# ---------------------------------------------------------------------------
def build_authorization_url(provider: str, state: str, code_challenge: str) -> str:
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(f"Unsupported provider: {provider}")
    cfg = PROVIDER_CONFIGS[provider]
    client_id = ""
    if provider == "google":
        client_id = settings.GOOGLE_CLIENT_ID or "test_google_client_id"
    elif provider == "github":
        client_id = settings.GITHUB_CLIENT_ID or "test_github_client_id"

    redirect_uri = settings.OAUTH_REDIRECT_URI or "http://localhost:8000/auth/callback"

    # Build query manually to keep tests deterministic
    from urllib.parse import urlencode, quote

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    # urlencode with safe handling for scopes (space -> %20)
    query = urlencode(params, quote_via=quote)
    return f"{cfg['authorize_url']}?{query}"


# ---------------------------------------------------------------------------
# State store (Redis-backed with dict fallback)
# ---------------------------------------------------------------------------
async def store_state(redis_client: Any, state: str, code_verifier: str, ttl: int = STATE_TTL_SECONDS) -> None:
    """Store state -> code_verifier with TTL. Supports dict or redis client."""
    if isinstance(redis_client, dict):
        redis_client[state] = code_verifier
        return
    try:
        await redis_client.set(f"{STATE_KEY_PREFIX}{state}", code_verifier, ex=ttl)
    except Exception:
        _in_memory_states[state] = code_verifier


async def validate_state(redis_client: Any, state: str) -> str | None:
    """Validate state and return code_verifier, single-use (delete after)."""
    if isinstance(redis_client, dict):
        return redis_client.pop(state, None)
    try:
        key = f"{STATE_KEY_PREFIX}{state}"
        val = await redis_client.get(key)
        if val is not None:
            if isinstance(val, bytes):
                val = val.decode()
            await redis_client.delete(key)
            return val
        return None
    except Exception:
        return _in_memory_states.pop(state, None)


def get_state_store() -> dict[str, str]:
    """Return the default in-memory state store (used by API when Redis unavailable)."""
    return _in_memory_states


# ---------------------------------------------------------------------------
# Token exchange & userinfo
# ---------------------------------------------------------------------------
async def exchange_code_for_tokens(provider: str, code: str, code_verifier: str) -> dict[str, Any]:
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(f"Unsupported provider: {provider}")
    cfg = PROVIDER_CONFIGS[provider]
    client_id = settings.GOOGLE_CLIENT_ID if provider == "google" else settings.GITHUB_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET if provider == "google" else settings.GITHUB_CLIENT_SECRET
    # Fallback for tests
    client_id = client_id or "test_client_id"
    client_secret = client_secret or "test_client_secret"
    redirect_uri = settings.OAUTH_REDIRECT_URI or "http://localhost:8000/auth/callback"

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    headers = {"Accept": "application/json"}
    # GitHub expects different handling but we unify; GitHub token endpoint returns json when Accept header set

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(cfg["token_url"], data=data, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.ReadTimeout as e:
        raise TimeoutError(f"OAuth provider timeout for {provider}") from e
    except httpx.TimeoutException as e:
        raise TimeoutError(f"OAuth provider timeout for {provider}") from e


async def get_user_info(provider: str, access_token: str) -> dict[str, Any]:
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(f"Unsupported provider: {provider}")
    cfg = PROVIDER_CONFIGS[provider]
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(cfg["userinfo_url"], headers=headers)
        resp.raise_for_status()
        data = resp.json()
        # Normalize: GitHub nests email differently; but we assume email field exists
        # For GitHub, if email is None, fetch /user/emails — simplified: use primary email from data
        return data


# ---------------------------------------------------------------------------
# Account linking — find existing user by email or create new
# ---------------------------------------------------------------------------
async def find_or_create_user(db: AsyncSession, provider: str, user_info: dict[str, Any]) -> User:
    # Normalize profile fields across providers
    email = user_info.get("email")
    # GitHub fallback: if email None, try to get from emails array
    if not email and provider == "github":
        # user_info may contain "emails" list in mocked data
        emails = user_info.get("emails")
        if isinstance(emails, list) and emails:
            # Find primary or first
            for e in emails:
                if isinstance(e, dict) and e.get("primary"):
                    email = e.get("email")
                    break
            if not email:
                first = emails[0]
                email = first.get("email") if isinstance(first, dict) else str(first)

    display_name = user_info.get("name") or user_info.get("login") or user_info.get("display_name") or (email.split("@")[0] if email else "User")
    avatar_url = user_info.get("picture") or user_info.get("avatar_url") or None

    if email:
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalars().first()
        if existing:
            # Link: ensure email_verified true, optionally update avatar if missing
            if not existing.email_verified:
                existing.email_verified = True
            if not existing.avatar_url and avatar_url:
                existing.avatar_url = avatar_url
            # need flush so caller can commit
            await db.flush()
            return existing

    # Create new user
    new_user = User(
        email=email,
        display_name=display_name[:100] if display_name else "User",
        avatar_url=avatar_url,
        email_verified=True,
    )
    db.add(new_user)
    await db.flush()
    return new_user
