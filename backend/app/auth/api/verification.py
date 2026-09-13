"""Email verification API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services.email import EmailService
from app.auth.services.email_verification import EmailVerificationService
from app.db.session import get_session

router = APIRouter(tags=["auth"])


class ResendRequest(BaseModel):
    """Request body for resending verification email."""

    email: str = Field(..., max_length=255)


class VerifyRequest(BaseModel):
    """Request body for verifying email with token."""

    token: str = Field(..., max_length=255)


# Redis accessor — patchable in tests
_redis_client = None


def get_redis():
    """Return redis client or dict fallback."""
    if _redis_client is not None:
        return _redis_client
    return {}


def set_redis(client):
    global _redis_client
    _redis_client = client


@router.get("/auth/verify")
async def verify_email_get(
    token: str,
    db: AsyncSession = Depends(get_session),
):
    """Verify email with token (GET for email links)."""
    from app.auth.models.user import User
    from sqlalchemy import select

    redis = get_redis()
    service = EmailVerificationService(redis_client=redis)

    user_id = await service.verify_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Update user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Email verified successfully"}


@router.post("/auth/verify")
async def verify_email_post(
    body: VerifyRequest,
    db: AsyncSession = Depends(get_session),
):
    """Verify email with token (POST for API)."""
    from app.auth.models.user import User
    from sqlalchemy import select

    redis = get_redis()
    service = EmailVerificationService(redis_client=redis)

    user_id = await service.verify_token(body.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Update user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Email verified successfully"}


@router.post("/auth/resend-verification")
async def resend_verification(
    body: ResendRequest,
    db: AsyncSession = Depends(get_session),
):
    """Resend verification email."""
    from app.auth.models.user import User
    from sqlalchemy import select

    redis = get_redis()
    service = EmailVerificationService(redis_client=redis)

    # Check rate limit
    # We need user_id for rate limiting, but we don't reveal if email exists
    # So we check rate limit after finding user
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user:
        # Check rate limit
        if not await service.can_resend(str(user.id)):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Try again later.",
            )

        # Generate new token
        token = await service.generate_token(str(user.id))

        # Send email
        email_service = EmailService()
        await email_service.send_verification(user.email, token)

        # Record resend
        await service.record_resend(str(user.id))

    # Always return success to prevent email enumeration
    return {"message": "If email exists, verification sent"}
