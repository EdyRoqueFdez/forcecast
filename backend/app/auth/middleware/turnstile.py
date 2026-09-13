"""Turnstile dependency — Cloudflare CAPTCHA verification for critical endpoints."""

import logging

import httpx
from fastapi import HTTPException, Request

from app.core.config import settings
from app.core.feature_flags import get_feature_flags

logger = logging.getLogger(__name__)

# Cloudflare Turnstile verification URL
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(
    token: str,
    remote_ip: str | None = None,
) -> bool:
    """Verify Turnstile token with Cloudflare.

    Args:
        token: The Turnstile response token
        remote_ip: Optional client IP for verification

    Returns:
        True if token is valid, False otherwise
    """
    secret_key = settings.TURNSTILE_SECRET_KEY
    if not secret_key:
        logger.warning("Turnstile secret key not configured")
        return False

    payload = {
        "secret": secret_key,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            data = resp.json()
            success = bool(data.get("success", False))
            if not success:
                logger.info(
                    "turnstile verification failed",
                    extra={"error_codes": data.get("error-codes")},
                )
            return success
    except Exception as e:
        logger.warning(f"turnstile verification error: {e}")
        return False


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check X-Forwarded-For first
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()

    # Fall back to client.host
    if request.client:
        return request.client.host

    return "unknown"


async def require_turnstile_registration(request: Request) -> str | None:
    """FastAPI dependency: verify Turnstile for registration.

    Returns token if valid, None if feature flag disabled.
    Raises HTTPException if verification fails.
    """
    feature_flags = get_feature_flags()
    enabled = await feature_flags.is_enabled("FEATURE_CAPTCHA_REGISTRATION")

    if not enabled:
        return None

    # Extract token from query params (OAuth callback) or body
    token = request.query_params.get("turnstile_token")

    if not token:
        try:
            body = await request.json()
            if isinstance(body, dict):
                token = body.get("turnstile_token")
        except Exception:
            pass

    if not token:
        raise HTTPException(
            status_code=403,
            detail="CAPTCHA token required for registration",
        )

    ip_address = _get_client_ip(request)
    is_valid = await verify_turnstile_token(token, ip_address)

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail="CAPTCHA verification failed",
        )

    return token


async def require_turnstile_vote(request: Request) -> str | None:
    """FastAPI dependency: verify Turnstile for voting.

    Returns token if valid, None if not triggered.
    Raises HTTPException if verification fails.
    """
    feature_flags = get_feature_flags()
    enabled = await feature_flags.is_enabled("FEATURE_CAPTCHA_VOTE")

    if not enabled:
        return None

    # Extract token from body
    token = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            token = body.get("turnstile_token")
    except Exception:
        pass

    # If no token provided and feature is enabled, check if triggered
    # (burst detection or first vote will be checked in the endpoint)
    # For now, if token is provided, verify it
    if token:
        ip_address = _get_client_ip(request)
        is_valid = await verify_turnstile_token(token, ip_address)

        if not is_valid:
            raise HTTPException(
                status_code=403,
                detail="CAPTCHA verification failed",
            )

    return token
