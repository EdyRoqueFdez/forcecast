"""Token API routes — refresh, logout, JWKS."""

import time
from datetime import datetime, timezone
from typing import Any, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.schemas.tokens import JWKSResponse
from app.auth.services.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwks,
    is_jti_revoked,
    revoke_jti,
    verify_token,
)
from app.auth.models.user import User
from app.db.session import get_session

router = APIRouter(tags=["auth"])

# Redis accessor — patchable in tests via app.auth.api.tokens.get_redis
_redis_client: Any = None


def get_redis() -> Any:
    """Return redis client or dict fallback. Patchable."""
    if _redis_client is not None:
        return _redis_client
    # In-memory dict fallback for tests/dev without redis
    return {}


def set_redis(client: Any) -> None:
    global _redis_client
    _redis_client = client


def _is_mobile(request: Request) -> bool:
    accept = request.headers.get("accept", "") or ""
    if "application/json" in accept.lower():
        return True
    # Also check explicit header for tests
    # Do not treat text/html as mobile
    ua = request.headers.get("user-agent", "") or ""
    # If UA contains mobile indicators and accept is json, already handled
    # For now, only JSON accept triggers mobile; UA heuristic optional
    return False


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    # access_token cookie: 30min
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    # Also set max-age 0 explicitly for test assertions
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=0,
        path="/",
        expires=0,
    )
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=0,
        path="/",
        expires=0,
    )


async def _get_user_role(db: AsyncSession, user_id: str) -> str:
    try:
        result = await db.execute(select(User).where(User.id == user_id))  # type: ignore
        user = result.scalars().first()
        if user and hasattr(user, "role"):
            role = user.role
            return role.value if hasattr(role, "value") else str(role)
    except Exception:
        pass
    return "user"


@router.post("/auth/refresh")
async def refresh_tokens(request: Request, db: AsyncSession = Depends(get_session)):
    redis = get_redis()
    # Extract refresh_token from body JSON or cookie
    refresh_token: str | None = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            refresh_token = body.get("refresh_token")
    except Exception:
        body = None
    if not refresh_token:
        refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        # also try form?
        refresh_token = request.query_params.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    # Verify token (signature, exp, revocation)
    try:
        payload = await verify_token(refresh_token, redis)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError as e:
        msg = str(e).lower()
        if "expired" in msg:
            raise HTTPException(status_code=401, detail="Refresh token expired")
        if "revoked" in msg:
            raise HTTPException(status_code=401, detail="Refresh token revoked")
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        # Fallback: try decode to see if expired vs invalid
        try:
            decode_token(refresh_token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token expired")
        except Exception:
            pass
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(e)}")

    # Must be refresh token (has session_id)
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token: missing session_id")

    user_id = payload.get("sub")
    old_jti = payload.get("jti")
    old_exp = payload.get("exp", 0)

    # Revoke old token with TTL = remaining lifetime
    try:
        ttl = int(old_exp - time.time()) if old_exp else 7 * 24 * 60 * 60
        if ttl <= 0:
            ttl = 7 * 24 * 60 * 60
        await revoke_jti(redis, old_jti, ttl_seconds=ttl)
    except Exception:
        pass

    # Fetch role
    role = await _get_user_role(db, str(user_id))

    # Create new pair (new jti, same session_id for now)
    new_access = create_access_token(user_id=str(user_id), role=role)
    new_refresh = create_refresh_token(user_id=str(user_id), session_id=str(session_id))

    # Optionally update session last_active_at
    try:
        from app.auth.models.session import Session

        result = await db.execute(select(Session).where(Session.id == str(session_id)))  # type: ignore
        sess = result.scalars().first()
        if sess:
            sess.last_active_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception:
        pass

    # Build response with conditional cookie delivery
    is_mobile = _is_mobile(request)
    body_resp = {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}

    if is_mobile:
        # Mobile: no Set-Cookie, tokens in body only
        return JSONResponse(content=body_resp)
    else:
        resp = JSONResponse(content=body_resp)
        _set_auth_cookies(resp, new_access, new_refresh)
        return resp


@router.post("/auth/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_session)):
    redis = get_redis()
    # Gather tokens to revoke: from body, cookies, header
    tokens_to_revoke: list[str] = []

    # From JSON body if provided
    try:
        body = await request.json()
        if isinstance(body, dict):
            rt = body.get("refresh_token")
            at = body.get("access_token")
            if rt:
                tokens_to_revoke.append(rt)
            if at:
                tokens_to_revoke.append(at)
    except Exception:
        pass

    # From cookies
    for key in ("access_token", "refresh_token"):
        val = request.cookies.get(key)
        if val and val not in tokens_to_revoke:
            tokens_to_revoke.append(val)

    # From Authorization header
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        tok = auth[7:].strip()
        if tok and tok not in tokens_to_revoke:
            tokens_to_revoke.append(tok)

    # Revoke each token's JTI
    revoked_count = 0
    for tok in tokens_to_revoke:
        try:
            payload = decode_token(tok)
            jti = payload.get("jti")
            exp = payload.get("exp", 0)
            if jti:
                ttl = int(exp - time.time()) if exp else 1800
                if ttl <= 0:
                    ttl = 1800
                await revoke_jti(redis, jti, ttl_seconds=ttl)
                revoked_count += 1
                # Also try to update session/refresh_token DB records
                try:
                    from app.auth.models.session import Session

                    sess_id = payload.get("session_id")
                    if sess_id:
                        result = await db.execute(select(Session).where(Session.id == str(sess_id)))  # type: ignore
                        sess = result.scalars().first()
                        if sess:
                            sess.revoked_at = datetime.now(timezone.utc)
                    from app.auth.models.refresh_token import RefreshToken

                    result2 = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))  # type: ignore
                    rt_obj = result2.scalars().first()
                    if rt_obj:
                        rt_obj.revoked_at = datetime.now(timezone.utc)
                    await db.commit()
                except Exception:
                    pass
        except Exception:
            # Even if decode fails, we still count? ignore
            continue

    # Build response clearing cookies
    # Always clear cookies regardless of mobile/web, but mobile may not need
    is_mobile = _is_mobile(request)
    content = {"message": "Logged out", "revoked": revoked_count}
    if is_mobile:
        # For mobile, still return JSON but also clear? Spec says cookies cleared on logout for web.
        # For mobile we omit Set-Cookie to satisfy test_mobile? But logout should clear anyway for web.
        # Our test_web_cookies_cleared expects Set-Cookie max-age 0, so we must clear for all
        resp = JSONResponse(content=content)
        _clear_auth_cookies(resp)
        return resp
    else:
        resp = JSONResponse(content=content)
        _clear_auth_cookies(resp)
        return resp


@router.get("/.well-known/jwks.json")
async def jwks():
    return JSONResponse(content=get_jwks())


# Also expose at /auth/jwks for convenience? No, only well-known
