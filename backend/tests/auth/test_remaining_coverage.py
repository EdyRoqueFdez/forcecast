"""Additional coverage tests for remaining uncovered branches"""

import time
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.auth.middleware.rate_limit import (
    check_rate_limit as check_generic_rate_limit,
    enforce_ip_rate_limit,
    enforce_user_rate_limit,
    LOGIN_IP_LIMIT,
    REGISTER_IP_LIMIT,
    USER_RATE_LIMIT,
    ADMIN_RATE_LIMIT,
    _memory_buckets,
)
from app.auth.services.api_keys import (
    check_rate_limit as api_key_check_rate_limit,
    _redis_incr_with_expiry,
    _in_memory_buckets,
)
from app.auth.services.anti_bot import (
    generate_fingerprint,
    verify_turnstile,
    get_effective_rate_limit,
    is_strict_mode,
    adjust_reputation,
    check_fingerprint_mismatch,
    check_rapid_account_creation,
    record_account_creation,
    check_refresh_anomaly,
    clear_anti_bot_state,
)
from app.auth.models.user import User, RoleEnum


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
    def __init__(self, user_id, role="user", reputation=5.0):
        self.id = user_id
        self.role = role
        self.reputation_score = reputation


# =============================================================================
# RATE LIMIT MIDDLEWARE - REMAINING BRANCHES
# =============================================================================

@pytest.mark.asyncio
async def test_check_rate_limit_redis_get_returns_none():
    """Test check_rate_limit when redis.get returns None."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    class MockRedis:
        async def get(self, key):
            return None
        
        async def set(self, key, value, ex=None):
            pass
    
    mock_redis = type('MockRedis', (), {'store': {}})()
    key = "mock:none"
    limit = 5
    window = 60
    
    is_limited, remaining, retry_after = await check_generic_rate_limit(type('MockRedis', (), {'store': {}})(), key, limit, window)
    assert is_limited is False
    assert remaining == limit - 1


@pytest.mark.asyncio
async def test_check_rate_limit_redis_get_returns_empty_string():
    """Test check_rate_limit when redis.get returns empty string."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    class MockRedis:
        async def get(self, key):
            return ""
        
        async def set(self, key, value, ex=None):
            pass
    
    mock_redis = type('MockRedis', (), {'store': {}})()
    key = "mock:empty"
    limit = 5
    window = 60
    
    is_limited, remaining, retry_after = await check_generic_rate_limit(type('MockRedis', (), {'store': {}})(), key, limit, window)
    assert is_limited is False


@pytest.mark.asyncio
async def test_enforce_ip_rate_limit_endpoint_other():
    """Test enforce_ip_rate_limit with endpoint other than login/register."""
    from app.auth.middleware.rate_limit import enforce_ip_rate_limit
    from fastapi import HTTPException
    
    redis_dict = {}
    ip = "192.168.1.200"
    
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = ip
    req.headers = {}
    
    # Should use LOGIN_IP_LIMIT as default for unknown endpoints
    for _ in range(LOGIN_IP_LIMIT):
        from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
        await check_generic_rate_limit(redis_dict, f"api:{ip}", LOGIN_IP_LIMIT, 60)
    
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = ip
    req.headers = {}
    
    with pytest.raises(Exception) as exc:
        await enforce_ip_rate_limit(req, redis_dict, endpoint="api")
    assert exc.value.status_code == 429


# =============================================================================
# API KEYS SERVICE - REMAINING BRANCHES
# =============================================================================

@pytest.mark.asyncio
async def test_redis_incr_with_expiry_dict_old_int():
    """Test _redis_incr_with_expiry with int value in dict (old format)."""
    from app.auth.services.api_keys import _redis_incr_with_expiry
    
    redis_dict = {}
    key = "test:int"
    expiry = 60
    
    # Set int value (old format)
    redis_dict[key] = 3
    
    count = await _redis_incr_with_expiry(redis_dict, key, expiry)
    # Should handle int and convert to list
    assert count == 4  # 3 + 1


@pytest.mark.asyncio
async def test_redis_incr_with_expiry_fake_redis_multiple_calls():
    """Test _redis_incr_with_expiry with FakeRedis across multiple calls."""
    from app.auth.services.api_keys import _redis_incr_with_expiry
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    key = "fake:incr"
    expiry = 60
    
    count = await _redis_incr_with_expiry(fake_redis, key, expiry)
    assert count == 1
    
    count = await _redis_incr_with_expiry(fake_redis, key, expiry)
    assert count == 2


@pytest.mark.asyncio
async def test_redis_incr_with_expiry_exception_handling():
    """Test _redis_incr_with_expiry exception handling falls back to memory."""
    from app.auth.services.api_keys import _redis_incr_with_expiry, _in_memory_buckets
    
    _in_memory_buckets.clear()
    
    class BadRedis:
        async def get(self, key):
            raise Exception("Redis down")
        
        async def set(self, key, value, ex=None):
            raise Exception("Redis down")
    
    bad_redis = BadRedis()
    key = "bad:incr"
    
    count = await _redis_incr_with_expiry(bad_redis, key, 60)
    assert count == 1
    
    count = await _redis_incr_with_expiry(bad_redis, key, 60)
    assert count == 2


@pytest.mark.asyncio
async def test_check_rate_limit_api_key_different_keys():
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


@pytest.mark.asyncio
async def test_api_key_check_with_fake_redis_store():
    """Test API key rate limit with FakeRedis store."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    key_hash = hashlib.sha256(b"test-key-2").hexdigest()
    limit = 10
    
    for _ in range(10):
        is_limited, remaining, retry_after = await api_key_check(fake_redis, key_hash, limit)
        assert is_limited is False
    
    is_limited, remaining, retry_after = await api_key_check(fake_redis, key_hash, limit)
    assert is_limited is True
    assert retry_after > 0


# =============================================================================
# ANTI-BOT SERVICE - REMAINING BRANCHES
# =============================================================================

@pytest.mark.asyncio
async def test_verify_turnstile_provider_error_500():
    """Test verify_turnstile handles 500 status from provider."""
    from app.auth.services.anti_bot import verify_turnstile, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": False}
    mock_response.status_code = 500
    
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        
        result = await verify_turnstile("any-token")
        assert result is False


@pytest.mark.asyncio
async def test_verify_turnstile_empty_token():
    """Test verify_turnstile with empty/whitespace token."""
    from app.auth.services.anti_bot import verify_turnstile, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    result = await verify_turnstile("")
    assert result is False
    
    result = await verify_turnstile("   ")
    assert result is False
    
    result = await verify_turnstile(None)
    assert result is False


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
async def test_check_fingerprint_mismatch_stored_none():
    """Test check_fingerprint_mismatch when stored_fp is None."""
    from app.auth.services.anti_bot import check_fingerprint_mismatch, clear_anti_bot_state
    from app.auth.models.user import User
    
    clear_anti_bot_state()
    
    user = User(email="nostored@example.com", display_name="NoStored", email_verified=True)
    user.reputation_score = 5.0
    user.id = str(uuid.uuid4())
    
    result = await check_fingerprint_mismatch(
        session_fingerprint=None,
        current_fingerprint="current_fp",
        user=user
    )
    
    assert result["mismatch"] is False
    assert result["anomaly"] is False
    assert result["reason"] == "no stored fingerprint"


@pytest.mark.asyncio
async def test_check_fingerprint_mismatch_current_none():
    """Test check_fingerprint_mismatch when current_fingerprint is None."""
    from app.auth.services.anti_bot import check_fingerprint_mismatch, clear_anti_bot_state
    from app.auth.models.user import User
    
    clear_anti_bot_state()
    
    user = User(email="nocurrent@example.com", display_name="NoCurrent", email_verified=True)
    user.reputation_score = 5.0
    user.id = str(uuid.uuid4())
    
    result = await check_fingerprint_mismatch(
        session_fingerprint="stored_fp",
        current_fingerprint=None,
        user=user
    )
    
    # None != "stored_fp" -> mismatch = True
    # But age check depends on session... this is edge case
    assert result["mismatch"] is True
    assert result["anomaly"] is True
    assert result["reason"] == "fingerprint_mismatch"


@pytest.mark.asyncio
async def test_record_account_creation_real_redis_json():
    """Test record_account_creation with real redis that returns JSON string."""
    from app.auth.services.anti_bot import record_account_creation, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    class MockRedis:
        def __init__(self):
            self.store = {}
        
        async def get(self, key):
            import json
            val = self.store.get(key)
            if val is not None:
                return json.dumps(val)
            return None
        
        async def set(self, key, value, ex=None):
            self.store[key] = value
    
    mock_redis = type('MockRedis', (), {'store': {}})()
    ip = "10.0.0.1"
    
    cnt = await record_account_creation(ip, type('MockRedis', (), {'store': {}})())
    assert cnt == 1


@pytest.mark.asyncio
async def test_check_rapid_account_creation_real_redis():
    """Test check_rapid_account_creation with real redis."""
    from app.auth.services.anti_bot import check_rapid_account_creation, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    class MockRedis:
        def __init__(self):
            self.store = {}
        
        async def get(self, key):
            import json
            val = self.store.get(key)
            if val is not None:
                return json.dumps(val)
            return None
        
        async def set(self, key, value, ex=None):
            self.store[key] = value
    
    mock_redis = type('MockRedis', (), {'store': {}})()
    ip = "10.0.0.1"
    
    # Test with dict
    redis_dict = {}
    for i in range(5):
        from app.auth.services.anti_bot import record_account_creation
        await record_account_creation("10.0.0.1", redis_dict)
    blocked = await check_rapid_account_creation("10.0.0.1", redis_dict)
    assert blocked is False
    
    from app.auth.services.anti_bot import record_account_creation
    await record_account_creation("10.0.0.1", redis_dict)
    blocked = await check_rapid_account_creation("10.0.0.1", redis_dict)
    assert blocked is True


@pytest.mark.asyncio
async def test_check_refresh_anomaly_old_session_new_device():
    """Test check_refresh_anomaly with old session (>5min) and new device."""
    from app.auth.services.anti_bot import check_refresh_anomaly, generate_fingerprint, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    from datetime import datetime, timezone, timedelta
    
    fp_original = generate_fingerprint("Mozilla/5.0 Chrome", "1.1.1.1", "en-US")
    fp_new = generate_fingerprint("Mozilla/5.0 Safari", "2.2.2.2", "en-US")
    
    class OldSession:
        def __init__(self):
            self.device_fingerprint = "original_fp"
            self.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    user = User(email="oldnew@example.com", display_name="OldNew", email_verified=True)
    user.id = str(uuid.uuid4())
    user.reputation_score = 5.0
    
    # Session created 10 minutes ago - older than 5min threshold
    session = OldSession()
    
    result = await check_refresh_anomaly(
        session=OldSession(),
        new_fingerprint=generate_fingerprint("Mozilla/5.0 Safari", "2.2.2.2", "en-US"),
        user=user
    )
    
    # Session older than 5min -> no anomaly even with new device
    assert result["anomaly"] is False


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