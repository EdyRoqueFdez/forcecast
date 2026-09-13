"""Email verification service — token generation and verification."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """Handle email verification tokens."""

    def __init__(self, redis_client: Any = None):
        self.redis = redis_client

    async def generate_token(self, user_id: str) -> str:
        """Generate verification token for user.

        Args:
            user_id: The user ID

        Returns:
            Verification token
        """
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.EMAIL_VERIFICATION_EXPIRY_HOURS
        )

        # Store in Redis
        if self.redis is not None:
            key = f"email_verify:{token}"
            if isinstance(self.redis, dict):
                self.redis[key] = {
                    "user_id": user_id,
                    "expires_at": expires_at.isoformat(),
                    "used": False,
                }
            else:
                # Real Redis
                await self.redis.set(
                    key,
                    {"user_id": user_id, "expires_at": expires_at.isoformat(), "used": False},
                    ex=settings.EMAIL_VERIFICATION_EXPIRY_HOURS * 3600,
                )

        return token

    async def verify_token(self, token: str) -> str | None:
        """Verify token and return user_id.

        Args:
            token: The verification token

        Returns:
            User ID if valid, None otherwise
        """
        if self.redis is None:
            return None

        key = f"email_verify:{token}"

        try:
            if isinstance(self.redis, dict):
                data = self.redis.get(key)
            else:
                data = await self.redis.get(key)

            if data is None:
                return None

            # Check if used
            if data.get("used"):
                return None

            # Check expiry
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                return None

            # Mark as used
            data["used"] = True
            if isinstance(self.redis, dict):
                self.redis[key] = data
            else:
                await self.redis.set(key, data)

            return data["user_id"]

        except Exception as e:
            logger.warning(f"token verification error: {e}")
            return None

    async def can_resend(self, user_id: str) -> bool:
        """Check if user can resend verification email.

        Args:
            user_id: The user ID

        Returns:
            True if can resend, False if rate limited
        """
        if self.redis is None:
            return True

        key = f"email_resend:{user_id}"

        try:
            if isinstance(self.redis, dict):
                count = self.redis.get(key, 0)
            else:
                count = await self.redis.get(key)
                count = int(count) if count else 0

            return count < settings.EMAIL_VERIFICATION_MAX_RESEND

        except Exception as e:
            logger.warning(f"resend check error: {e}")
            return True

    async def record_resend(self, user_id: str) -> None:
        """Record resend attempt for rate limiting.

        Args:
            user_id: The user ID
        """
        if self.redis is None:
            return

        key = f"email_resend:{user_id}"

        try:
            if isinstance(self.redis, dict):
                count = self.redis.get(key, 0)
                self.redis[key] = count + 1
            else:
                count = await self.redis.incr(key)
                if count == 1:
                    await self.redis.expire(key, 3600)  # 1 hour window

        except Exception as e:
            logger.warning(f"resend record error: {e}")

    async def invalidate_user_tokens(self, user_id: str) -> None:
        """Invalidate all tokens for a user.

        Args:
            user_id: The user ID
        """
        if self.redis is None:
            return

        # This is a simplified version; in production you'd track tokens per user
        pass
