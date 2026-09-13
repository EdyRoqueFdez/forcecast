"""Burst detection service — detect rapid voting patterns.

Uses Redis sliding window to detect burst voting behavior.
When detected, triggers CAPTCHA verification.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Default burst detection settings
BURST_WINDOW_SECONDS = 10  # Time window to check
BURST_THRESHOLD = 2  # Number of votes to trigger burst


class BurstDetector:
    """Detect burst voting patterns using Redis sliding window."""

    def __init__(self, redis_client: Any = None):
        self.redis = redis_client

    async def is_burst(
        self,
        user_id: str,
        window_seconds: int = BURST_WINDOW_SECONDS,
        threshold: int = BURST_THRESHOLD,
    ) -> bool:
        """Check if user is voting in burst mode.

        Args:
            user_id: The user ID to check
            window_seconds: Time window in seconds
            threshold: Number of votes to trigger burst

        Returns:
            True if burst detected, False otherwise
        """
        if self.redis is None:
            logger.warning("Redis not available for burst detection")
            return False

        key = f"vote_burst:{user_id}"
        now = time.time()

        try:
            # Get all timestamps in the window
            if isinstance(self.redis, dict):
                # Dict fallback for testing
                raw = self.redis.get(key)
                if raw is None:
                    count = 0
                elif isinstance(raw, list):
                    count = sum(1 for t in raw if now - t < window_seconds)
                else:
                    count = 0
            elif hasattr(self.redis, "zrangebyscore"):
                # Real Redis - use sorted sets
                timestamps = await self.redis.zrangebyscore(
                    key, now - window_seconds, now
                )
                count = len(timestamps) if timestamps else 0
            elif hasattr(self.redis, "get"):
                # Fake Redis with .get()
                raw = await self.redis.get(key)
                if raw is None:
                    count = 0
                elif isinstance(raw, list):
                    # Filter to window
                    count = sum(1 for t in raw if now - t < window_seconds)
                else:
                    count = 0
            else:
                count = 0

            return count >= threshold

        except Exception as e:
            logger.warning(f"burst detection error: {e}")
            return False

    async def record_vote(
        self,
        user_id: str,
        window_seconds: int = BURST_WINDOW_SECONDS,
    ) -> None:
        """Record vote timestamp for burst detection.

        Args:
            user_id: The user ID
            window_seconds: Time window for cleanup
        """
        if self.redis is None:
            return

        key = f"vote_burst:{user_id}"
        now = time.time()

        try:
            if isinstance(self.redis, dict):
                # Dict fallback for testing
                timestamps = self.redis.get(key, [])
                if not isinstance(timestamps, list):
                    timestamps = []
                timestamps.append(now)
                timestamps = [t for t in timestamps if now - t < window_seconds]
                self.redis[key] = timestamps
                logger.debug(f"record_vote: dict path, key={key}, timestamps={timestamps}")
            elif hasattr(self.redis, "zadd"):
                # Real Redis - use sorted sets
                await self.redis.zadd(key, {str(now): now})
                # Clean old entries
                await self.redis.zremrangebyscore(key, 0, now - window_seconds)
                # Set expiry
                await self.redis.expire(key, window_seconds)
            elif hasattr(self.redis, "get"):
                # Fake Redis with dict-like storage
                raw = await self.redis.get(key)
                if raw is None:
                    timestamps = []
                elif isinstance(raw, list):
                    timestamps = raw
                else:
                    timestamps = []
                timestamps.append(now)
                # Clean old
                timestamps = [t for t in timestamps if now - t < window_seconds]
                if hasattr(self.redis, "set"):
                    await self.redis.set(key, timestamps, ex=window_seconds)
        except Exception as e:
            logger.warning(f"burst record error: {e}")

    async def clear(self, user_id: str) -> None:
        """Clear burst data for a user.

        Args:
            user_id: The user ID
        """
        if self.redis is None:
            return

        key = f"vote_burst:{user_id}"

        try:
            if isinstance(self.redis, dict):
                self.redis.pop(key, None)
            elif hasattr(self.redis, "delete"):
                await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"burst clear error: {e}")
