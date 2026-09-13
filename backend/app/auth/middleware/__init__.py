"""Auth middleware package — unified exports for Phase 6 (consolidated)."""

from app.auth.middleware.auth import (  # noqa: F401
    AUTH_EXEMPT_ENDPOINTS,
    PUBLIC_ENDPOINTS,
    get_current_user,
    get_current_user_or_api_key,
    is_auth_exempt_path,
    is_public_path,
    require_admin,
    require_api_key,
)
from app.auth.middleware.rate_limit import (  # noqa: F401
    ADMIN_RATE_LIMIT,
    LOGIN_IP_LIMIT,
    REGISTER_IP_LIMIT,
    USER_RATE_LIMIT,
    check_rate_limit,
    clear_rate_limit_state,
    enforce_ip_rate_limit,
    enforce_user_rate_limit,
)

__all__ = [
    "ADMIN_RATE_LIMIT",
    "AUTH_EXEMPT_ENDPOINTS",
    "LOGIN_IP_LIMIT",
    "PUBLIC_ENDPOINTS",
    "REGISTER_IP_LIMIT",
    "USER_RATE_LIMIT",
    "check_rate_limit",
    "clear_rate_limit_state",
    "enforce_ip_rate_limit",
    "enforce_user_rate_limit",
    "get_current_user",
    "get_current_user_or_api_key",
    "is_auth_exempt_path",
    "is_public_path",
    "require_admin",
    "require_api_key",
]
