"""OAuth API routes — login, callback, error."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
        # Map other provider errors to 502
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

    # For Phase 2, return user JSON (Phase 3 will add JWT issuance)
    return JSONResponse(
        content={
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "email_verified": user.email_verified,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }
    )


@router.get("/error")
async def auth_error(request: Request):
    message = request.query_params.get("message", "unknown_error")
    return JSONResponse(content={"error": message, "message": message}, status_code=400)
