"""Profile API routes — GET /auth/me, PATCH /auth/me."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.middleware.auth import get_current_user
from app.auth.models.user import User, VisibilityMode
from app.auth.schemas.profile import ProfileResponse, ProfileUpdateRequest, ProfileUpdateResponse
from app.db.session import get_session

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=ProfileResponse)
async def get_profile(
    user: User = Depends(get_current_user),
):
    """Get current user profile. Requires authentication."""
    return ProfileResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        reputation_score=user.reputation_score,
        email_verified=user.email_verified,
        bio=user.bio,
        preferred_locale=user.preferred_locale,
        visibility_mode=user.visibility_mode.value if hasattr(user.visibility_mode, "value") else str(user.visibility_mode),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/auth/me", response_model=ProfileUpdateResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update current user profile. Requires authentication."""
    # Update only provided fields
    update_data = payload.model_dump(exclude_unset=True)

    if "display_name" in update_data:
        user.display_name = update_data["display_name"]

    if "avatar_url" in update_data:
        user.avatar_url = update_data["avatar_url"]

    if "bio" in update_data:
        user.bio = update_data["bio"]

    if "preferred_locale" in update_data:
        user.preferred_locale = update_data["preferred_locale"]

    if "visibility_mode" in update_data:
        mode = update_data["visibility_mode"]
        user.visibility_mode = VisibilityMode.PSEUDONYM if mode == "pseudonym" else VisibilityMode.PUBLIC

    await db.commit()
    await db.refresh(user)

    return ProfileUpdateResponse(
        message="Profile updated",
        profile=ProfileResponse(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            reputation_score=user.reputation_score,
            email_verified=user.email_verified,
            bio=user.bio,
            preferred_locale=user.preferred_locale,
            visibility_mode=user.visibility_mode.value if hasattr(user.visibility_mode, "value") else str(user.visibility_mode),
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )
