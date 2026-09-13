"""Auth API routers package."""

from app.auth.api.api_keys import router as api_keys_router  # noqa: F401
from app.auth.api.oauth import router as oauth_router  # noqa: F401
from app.auth.api.tokens import router as tokens_router  # noqa: F401
from app.auth.api.verification import router as verification_router  # noqa: F401

__all__ = ["api_keys_router", "oauth_router", "tokens_router", "verification_router"]
