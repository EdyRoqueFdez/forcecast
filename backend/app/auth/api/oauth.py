"""OAuth API routes — login, callback, error."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.services.jwt import create_access_token, create_refresh_token
from app.auth.services.oauth import (
    _in_memory_states,
    build_authorization_url,
    exchange_code_for_tokens,
    find_or_create_user,
    generate_code_challenge,
    generate_code_verifier,
    generate_state_token,
    get_user_info,
    store_state,
    validate_state,
)
from app.auth.models.refresh_token import RefreshToken
from app.auth.models.session import Session
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login/{provider}")
async def login(provider: str):
    if provider not in ("google", "github"):
        raise HTTPException(status_code=404, detail="Unsupported provider")
    state = generate_state_token()
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    # Store state->verifier (use in-memory fallback)
    await store_state(_in_memory_states, state, verifier, ttl=600)
    auth_url = build_authorization_url(provider, state, challenge)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback/{provider}")
async def callback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    if provider not in ("google", "github"):
        raise HTTPException(status_code=404, detail="Unsupported provider")

    query = request.query_params
    error = query.get("error")
    if error:
        # Spec: redirect to /auth/error?message=access_denied
        return RedirectResponse(url=f"/auth/error?message={error}", status_code=302)

    code = query.get("code")
    state = query.get("state")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    # Validate state (single-use)
    code_verifier = await validate_state(_in_memory_states, state)
    if code_verifier is None:
        raise HTTPException(status_code=403, detail="Invalid state")

    # Exchange code for tokens
    try:
        token_data = await exchange_code_for_tokens(provider, code, code_verifier)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail="OAuth provider timeout") from e
    except Exception as e:
        if "timeout" in str(e).lower():
            raise HTTPException(status_code=504, detail="OAuth provider timeout") from e
        raise HTTPException(status_code=502, detail=f"OAuth exchange failed: {str(e)}") from e

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="No access_token from provider")

    # Get user info
    try:
        user_info = await get_user_info(provider, access_token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch user info: {str(e)}") from e

    # Account linking / user creation
    user = await find_or_create_user(db, provider, user_info)
    await db.commit()
    await db.refresh(user)

    # Create session
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user.id,
        user_agent=request.headers.get("user-agent", ""),
        ip_address=request.client.host if request.client else None,
        created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()

    # Create JWT tokens
    user_id = str(user.id)
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_jwt = create_access_token(user_id=user_id, role=role)
    refresh_jwt = create_refresh_token(user_id=user_id, session_id=str(session.id))

    # Save refresh token to DB
    from app.auth.services.jwt import decode_token

    refresh_payload = decode_token(refresh_jwt)
    refresh_token_db = RefreshToken(
        jti=refresh_payload.get("jti"),
        user_id=user.id,
        session_id=session.id,
        expires_at=datetime.fromtimestamp(refresh_payload.get("exp", 0), tz=timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db.add(refresh_token_db)
    await db.commit()

    # Determine if mobile or web
    accept = request.headers.get("accept", "") or ""
    is_mobile = "application/json" in accept.lower()

    if is_mobile:
        # Mobile: return tokens in JSON body
        return JSONResponse(
            content={
                "access_token": access_jwt,
                "refresh_token": refresh_jwt,
                "token_type": "bearer",
                "user": {
                    "id": user_id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "avatar_url": user.avatar_url,
                    "role": role,
                },
            }
        )
    else:
        # Web: set cookies and redirect to frontend
        frontend_url = str(request.base_url).rstrip("/")
        response = RedirectResponse(
            url=f"{frontend_url}/auth/callback",
            status_code=302,
        )
        # Set httpOnly cookies
        response.set_cookie(
            key="access_token",
            value=access_jwt,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=30 * 60,  # 30 minutes
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_jwt,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/",
        )
        return response


@router.get("/error")
async def auth_error(request: Request):
    message = request.query_params.get("message", "unknown_error")
    return JSONResponse(content={"error": message, "message": message}, status_code=400)
