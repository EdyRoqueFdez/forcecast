"""Feature flag service — PostHog integration for gradual rollouts."""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Feature flag service using PostHog or local config fallback."""

    def __init__(self, posthog_client: Any = None):
        self.client = posthog_client

    @classmethod
    def create(cls) -> "FeatureFlags":
        """Create FeatureFlags instance with PostHog if configured."""
        client = None
        if settings.POSTHOG_API_KEY:
            try:
                from posthog import Posthog

                client = Posthog(
                    settings.POSTHOG_API_KEY,
                    host=settings.POSTHOG_HOST,
                )
            except ImportError:
                logger.warning("posthog not installed, feature flags disabled")
            except Exception as e:
                logger.warning(f"posthog init failed: {e}")

        return cls(posthog_client=client)

    async def is_enabled(
        self,
        flag_name: str,
        user_id: str | None = None,
        default: bool = False,
    ) -> bool:
        """Check if feature flag is enabled.

        Args:
            flag_name: The feature flag name
            user_id: Optional user ID for flag evaluation
            default: Default value if flag not found

        Returns:
            True if flag is enabled, False otherwise
        """
        # Check local config first (for overrides)
        local_value = getattr(settings, flag_name, None)
        if local_value is not None:
            return bool(local_value)

        # Fall back to PostHog
        if not self.client:
            return default

        try:
            distinct_id = user_id or "anonymous"
            return self.client.feature_enabled(
                flag_name,
                distinct_id,
                groups={"project": "forcecast"},
            )
        except Exception as e:
            logger.warning(f"feature flag check failed for {flag_name}: {e}")
            return default

    async def get_variant(
        self,
        flag_name: str,
        user_id: str | None = None,
        default: str | None = None,
    ) -> str | None:
        """Get feature flag variant.

        Args:
            flag_name: The feature flag name
            user_id: Optional user ID for flag evaluation
            default: Default variant if not found

        Returns:
            The variant name or default
        """
        if not self.client:
            return default

        try:
            distinct_id = user_id or "anonymous"
            return self.client.get_feature_flag(
                flag_name,
                distinct_id,
                groups={"project": "forcecast"},
            )
        except Exception as e:
            logger.warning(f"feature flag variant check failed for {flag_name}: {e}")
            return default


# Singleton instance
_feature_flags: FeatureFlags | None = None


def get_feature_flags() -> FeatureFlags:
    """Get or create FeatureFlags singleton."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags.create()
    return _feature_flags
