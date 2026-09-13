"""Additional coverage tests for rate_limit.py service"""

import hashlib
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.auth.services.api_keys import (
    check_rate_limit as api_key_check_rate_limit,
    _redis_incr_with_expiry,
    _in_memory_buckets,
)
from app.auth.middleware.rate_limit import (
    check_rate_limit as check_generic_rate_limit,
    enforce_ip_rate_limit,
    enforce_user_rate_limit,
    check_rate_limit as middleware_check_rate_limit,
    LOGIN_IP_LIMIT,
    REGISTER_IP_LIMIT,
    USER_RATE_LIMIT,
    ADMIN_RATE_LIMIT,
)
from app.auth.models.user import User, RoleEnum
from app.auth.services.anti_bot import clear_anti_bot_state, generate_fingerprint

class FakeRedis:
    def __init__(self):
        self.store = {}
        self.published = []
    
    async def get(self, key):
        return self.store.get(key)
    
    async def set(self, key, value, ex=None):
        self.store[key] = value
    
    async def publish(self, channel, message):
        self.published.append((channel, message))
        return 1
    
    async def delete(self, key):
        self.store.pop(key, None)


class FakeRequest:
    """Mock FastAPI Request object."""
    def __init__(self, ip="127.0.0.1", user_agent="test", headers=None):
        self.headers = headers or {}
        if "x-forwarded-for" not in self.headers:
            self.headers["x-forwarded-for"] = "10.0.0.1"
        self.client = MagicMock()
        self.client.host = "127.0.0.1"
        self.state = MagicMock()
        self.state.user = None
        self.state.api_key_id = None


class FakeUser:
    """Mock user for rate limit tests."""
    def __init__(self, user_id, role="user", reputation=5.0):
        self.id = user_id
        self.role = role
        self.reputation_score = reputation


class FakeAPIKey:
    """Mock API key for rate limit tests."""
    def __init__(self, key_hash, rate_limit=60, scopes=None):
        self.id = uuid.uuid4()
        self.key_hash = key_hash
        self.rate_limit = rate_limit
        self.scopes = scopes or ["read:models"]
        self.revoked_at = None


# =============================================================================
# RATE LIMIT MIDDLEWARE - ADDITIONAL COVERAGE
# =============================================================================

@pytest.mark.asyncio
async def test_check_generic_rate_limit_int_val_conversion():
    """Test check_rate_limit handles int value from old fixed window."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    redis_dict = {}
    key = "test:int"
    limit = 5
    window = 60
    
    # Simulate old int value (fixed window count)
    import time
    redis_dict[key] = 3  # int value from old implementation
    
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis_dict, key, limit, window)
    assert is_limited is False
    # Should handle int by converting to list approximation


@pytest.mark.asyncio
async def test_check_generic_rate_limit_empty_times_list():
    """Test check_rate_limit with empty times list."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    redis_dict = {}
    key = "test:empty"
    limit = 5
    window = 60
    
    redis_dict[key] = []  # empty list
    
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis_dict, key, limit, window)
    assert is_limited is False
    assert remaining == limit - 1


@pytest.mark.asyncio
async def test_check_generic_rate_limit_retry_after_calculation():
    """Test retry_after calculation."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    redis_dict = {}
    key = "test:retry"
    limit = 2
    window = 60
    
    # Add one timestamp
    import time
    redis_dict[key] = [time.time() - 10]  # 10 seconds ago
    
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis_dict, key, limit, window)
    assert is_limited is False
    assert retry_after > 0
    assert retry_after <= window


@pytest.mark.asyncio
async def test_check_generic_rate_limit_exact_limit():
    """Test when count exactly equals limit."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    redis_dict = {}
    key = "test:exact"
    limit = 3
    window = 60
    
    # Fill exactly to limit using same dict
    for _ in range(limit):
        is_limited, remaining, retry_after = await check_generic_rate_limit(redis_dict, key, limit, 60)
        assert is_limited is False
    
    # Next should be limited (>= limit)
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis_dict, key, limit, 60)
    assert is_limited is True
    assert remaining == 0


@pytest.mark.asyncio
async def test_enforce_ip_rate_limit_different_endpoints():
    """Test IP rate limit tracks different endpoints separately."""
    from app.auth.middleware.rate_limit import enforce_ip_rate_limit, check_rate_limit as check_generic_rate_limit
    from fastapi import HTTPException
    
    redis_dict = {}
    ip = "192.168.1.100"
    
    # Fill login limit using same dict
    for _ in range(LOGIN_IP_LIMIT):
        await check_generic_rate_limit(redis_dict, f"login:{ip}", LOGIN_IP_LIMIT, 60)
    
    # Login should be limited
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = ip
    req.headers = {}
    
    with pytest.raises(Exception) as exc:
        await enforce_ip_rate_limit(req, redis_dict, endpoint="login")
    assert exc.value.status_code == 429
    
    # Register should still work (different bucket)
    req2 = MagicMock()
    req2.client = MagicMock()
    req2.client.host = ip
    req2.headers = {}
    
    # Register endpoint should have its own counter
    try:
        await enforce_ip_rate_limit(req2, redis_dict, endpoint="register")
    except Exception:
        pytest.fail("Register endpoint should not be limited when login is")


# =============================================================================
# API KEYS SERVICE - REDIS INCR COVERAGE
# =============================================================================

@pytest.mark.asyncio
async def test_redis_incr_with_expiry_dict():
    """Test _redis_incr_with_expiry with dict fallback."""
    from app.auth.services.api_keys import _redis_incr_with_expiry
    
    redis_dict = {}
    key = "test:incr"
    expiry = 60
    
    # First call
    count = await _redis_incr_with_expiry(redis_dict, key, expiry)
    assert count == 1
    
    # Second call
    count = await _redis_incr_with_expiry(redis_dict, key, expiry)
    assert count == 2


@pytest.mark.asyncio
async def test_redis_incr_with_expiry_fake_redis():
    """Test _redis_incr_with_expiry with FakeRedis."""
    from app.auth.services.api_keys import _redis_incr_with_expiry
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    key = "fake:incr"
    expiry = 60
    
    count = await _redis_incr_with_expiry(fake_redis, key, expiry)
    assert count == 1
    
    count = await _redis_incr_with_expiry(fake_redis, key, expiry)
    assert count == 2


@pytest.mark.asyncio
async def test_redis_incr_with_expiry_real_redis_mock():
    """Test _redis_incr_with_expiry with real redis mock."""
    from app.auth.services.api_keys import _redis_incr_with_expiry
    import inspect
    
    class MockRedis:
        def __init__(self):
            self.store = {}
        
        async def get(self, key):
            return self.store.get(key)
        
        async def set(self, key, value, ex=None):
            self.store[key] = value
    
    mock_redis = MockRedis()
    key = "mock:incr"
    expiry = 60
    
    count = await _redis_incr_with_expiry(mock_redis, key, expiry)
    assert count == 1
    
    count = await _redis_incr_with_expiry(mock_redis, key, expiry)
    assert count == 2


@pytest.mark.asyncio
async def test_redis_incr_with_expiry_exception_fallback():
    """Test _redis_incr_with_expiry falls back to in-memory on exception."""
    from app.auth.services.api_keys import _redis_incr_with_expiry, _in_memory_buckets
    
    # Clear global buckets
    _in_memory_buckets.clear()
    
    # Redis that always fails
    class BadRedis:
        async def get(self, key):
            raise Exception("Redis down")
        
        async def set(self, key, value, ex=None):
            raise Exception("Redis down")
    
    bad_redis = BadRedis()
    key = "bad:incr"
    
    count = await _redis_incr_with_expiry(bad_redis, key, 60)
    assert count == 1  # Falls back to in-memory
    
    count = await _redis_incr_with_expiry(bad_redis, key, 60)
    assert count == 2


# =============================================================================
# API KEYS SERVICE - CHECK RATE LIMIT EDGE CASES
# =============================================================================

@pytest.mark.asyncio
async def test_api_key_check_rate_limit_sliding_window():
    """Test API key rate limit with sliding window behavior."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    
    redis_dict = {}
    key_hash = hashlib.sha256(b"sliding-test").hexdigest()
    limit = 5
    
    # First 5 should succeed
    for i in range(5):
        is_limited, remaining, retry_after = await api_key_check(redis_dict, key_hash, 5)
        assert is_limited is False
        assert remaining == 5 - i - 1
    
    # 6th should be limited
    is_limited, remaining, retry_after = await api_key_check(redis_dict, key_hash, 5)
    assert is_limited is True
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_api_key_check_rate_limit_different_keys():
    """Test different API keys have independent limits."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    import hashlib
    
    redis_dict = {}
    key1 = hashlib.sha256(b"key1").hexdigest()
    key2 = hashlib.sha256(b"key2").hexdigest()
    limit = 3
    
    # Fill key1 to limit
    for _ in range(3):
        is_limited, _, _ = await api_key_check(redis_dict, key1, 3)
        assert is_limited is False
    
    # key1 should be limited
    is_limited, _, _ = await api_key_check(redis_dict, key1, 3)
    assert is_limited is True
    
    # key2 should still work
    is_limited, remaining, _ = await api_key_check(redis_dict, hashlib.sha256(b"key2").hexdigest(), 3)
    assert is_limited is False
    assert remaining == 2


# =============================================================================
# ANTI-BOT SERVICE - MISSING BRANCHES
# =============================================================================

@pytest.mark.asyncio
async def test_verify_turnstile_invalid_json():
    """Test verify_turnstile handles invalid JSON response."""
    from app.auth.services.anti_bot import verify_turnstile, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.status_code = 200
    
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        
        result = await verify_turnstile("any-token")
        assert result is False


@pytest.mark.asyncio
async def test_verify_turnstile_non_200_status():
    """Test verify_turnstile handles non-200 status."""
    from app.auth.services.anti_bot import verify_turnstile, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True}
    mock_response.status_code = 429  # Rate limited by provider
    
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        
        result = await verify_turnstile("any-token")
        assert result is True  # Still returns success from provider response


@pytest.mark.asyncio
async def test_check_refresh_anomaly_created_at_none():
    """Test check_refresh_anomaly when created_at is None."""
    from app.auth.services.anti_bot import check_refresh_anomaly, generate_fingerprint, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    fp = generate_fingerprint("Mozilla/5.0 Chrome", "1.1.1.1", "en-US")
    
    class FakeSession:
        def __init__(self, fp):
            self.device_fingerprint = fp
            self.created_at = None
            self.last_active_at = None
    
    user = User(email="nocreated@example.com", display_name="NoCreated", email_verified=True)
    user.id = str(uuid.uuid4())
    user.reputation_score = 5.0
    
    result = await check_refresh_anomaly(
        session=FakeSession(fp),
        new_fingerprint=fp,
        user=user
    )
    
    assert result["anomaly"] is False
    # When created_at is None, age=999999, so no anomaly even with mismatch
    # With same fingerprint (fp), returns "refresh_normal"
    assert result["reason"] == "refresh_normal"


@pytest.mark.asyncio
async def test_check_refresh_anomaly_session_no_attrs():
    """Test check_refresh_anomaly when session has no attributes."""
    from app.auth.services.anti_bot import check_refresh_anomaly, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    class FakeSession:
        def __init__(self):
            pass  # No attributes
    
    user = User(email="noattrs@example.com", display_name="NoAttrs", email_verified=True)
    user.id = str(uuid.uuid4())
    user.reputation_score = 5.0
    
    result = await check_refresh_anomaly(
        session=FakeSession(),
        new_fingerprint="some_fp",
        user=user
    )
    
    assert result["anomaly"] is False
    assert result["reason"] == "no stored fingerprint"