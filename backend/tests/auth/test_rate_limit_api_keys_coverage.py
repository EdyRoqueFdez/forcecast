"""Additional coverage tests for uncovered branches in rate_limit.py and api_keys.py service"""

import hashlib
import time
import uuid
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
)
from app.auth.services.api_keys import (
    generate_api_key,
    hash_api_key,
    validate_scopes,
    validate_rate_limit,
    check_rate_limit as api_key_check_rate_limit,
    ALLOWED_SCOPES,
)
from app.auth.schemas.api_keys import APIKeyCreate, APIKeyRead, APIKeyCreateResponse, APIKeyList
from app.auth.models.user import User, RoleEnum


class FakeRedis:
    """Fake Redis with async methods for rate limiting tests."""
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
# RATE LIMIT MIDDLEWARE COVERAGE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_check_generic_rate_limit_dict_redis():
    """Test check_rate_limit with dict redis."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    redis_dict = {}
    key = "test:key"
    limit = 5
    window = 60
    
    # First 5 should succeed
    for i in range(limit):
        is_limited, remaining, retry_after = await check_generic_rate_limit(redis_dict, key, limit, window)
        assert is_limited is False
        assert remaining == limit - i - 1
    
    # 6th should be limited
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis_dict, key, limit, window)
    assert is_limited is True
    assert remaining == 0
    assert retry_after > 0
    assert retry_after <= window


@pytest.mark.asyncio
async def test_check_generic_rate_limit_fake_redis():
    """Test check_rate_limit with FakeRedis (has store attribute)."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    key = "fake:key"
    limit = 3
    window = 60
    
    # First 3 should succeed
    for i in range(limit):
        is_limited, remaining, retry_after = await check_generic_rate_limit(fake_redis, key, limit, window)
        assert is_limited is False
        assert remaining == limit - i - 1
    
    # 4th should be limited
    is_limited, remaining, retry_after = await check_generic_rate_limit(fake_redis, key, limit, window)
    assert is_limited is True
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_check_generic_rate_limit_window_cleaning():
    """Test that old timestamps are cleaned from window."""
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    
    redis_dict = {}
    key = "test:window"
    limit = 3  # limit 3, so after adding 1 we have 2
    window = 60
    
    # Add timestamps manually - one old (outside window), one recent
    import time
    now = time.time()
    redis_dict[key] = [now - 120, now - 10]  # one old (120s ago), one recent (10s ago)
    
    # Should clean old timestamp, only 1 recent remains, then add new = 2 total
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis_dict, key, limit, window)
    assert is_limited is False
    assert remaining == 1  # limit(3) - 2 = 1


@pytest.mark.asyncio
async def test_enforce_ip_rate_limit_login():
    """Test enforce_ip_rate_limit for login endpoint."""
    from app.auth.middleware.rate_limit import enforce_ip_rate_limit
    from fastapi import HTTPException
    
    redis_dict = {}
    ip = "192.168.1.100"
    
    # Fill to limit
    for _ in range(LOGIN_IP_LIMIT):
        from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
        await check_generic_rate_limit(redis_dict, f"login:{ip}", LOGIN_IP_LIMIT, window=60)
    
    # Next request should raise 429
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = ip
    req.headers = {}
    
    with pytest.raises(Exception) as exc:
        await enforce_ip_rate_limit(req, redis_dict, endpoint="login")
    
    assert exc.value.status_code == 429
    assert "retry-after" in {k.lower() for k in (exc.value.headers or {})}


@pytest.mark.asyncio
async def test_enforce_ip_rate_limit_register():
    """Test enforce_ip_rate_limit for register endpoint."""
    from app.auth.middleware.rate_limit import enforce_ip_rate_limit
    from fastapi import HTTPException
    
    redis_dict = {}
    ip = "192.168.1.50"
    
    # Fill to register limit
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    for _ in range(REGISTER_IP_LIMIT):
        await check_generic_rate_limit(redis_dict, f"register:192.168.1.50", REGISTER_IP_LIMIT, window=60)
    
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "192.168.1.50"
    req.headers = {}
    
    with pytest.raises(Exception) as exc:
        await enforce_ip_rate_limit(req, redis_dict, endpoint="register")
    
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_enforce_user_rate_limit():
    """Test enforce_user_rate_limit dependency."""
    from app.auth.middleware.rate_limit import enforce_user_rate_limit
    from fastapi import HTTPException
    
    redis_dict = {}
    user_id = str(uuid.uuid4())
    
    class FakeReq:
        def __init__(self, user):
            self.state = MagicMock()
            self.state.user = user
    
    user = User(email="rate@example.com", display_name="Rate", email_verified=True)
    user.id = str(uuid.uuid4())
    user.reputation_score = 5.0
    user.role = RoleEnum.USER
    
    # Fill to limit using the check function
    from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
    key = f"user:{str(uuid.uuid4())}"
    redis_dict = {}
    for _ in range(USER_RATE_LIMIT):
        await check_generic_rate_limit(redis_dict, f"user:{str(uuid.uuid4())}", USER_RATE_LIMIT, window=60)
    
    # Actually test with same user
    test_user = User(email="test@example.com", display_name="Test", email_verified=True, role=RoleEnum.USER)
    test_user.id = "test-user-123"
    test_user.reputation_score = 5.0
    
    # Fill rate limit for this user
    redis_test = {}
    for _ in range(USER_RATE_LIMIT):
        from app.auth.middleware.rate_limit import check_rate_limit as check_generic_rate_limit
        await check_generic_rate_limit(redis_test, f"user:test-user-123", USER_RATE_LIMIT, window=60)
    
    req = MagicMock()
    req.state = MagicMock()
    req.state.user = FakeUser("test-user-123", "user", 5.0)
    req.state.user.id = "test-user-123"
    
    with pytest.raises(Exception) as exc:
        await enforce_user_rate_limit(MagicMock(), redis_test, user=FakeUser("test-user-123", "user", 5.0))
    
    assert exc.value.status_code == 429


# =============================================================================
# API KEYS SERVICE COVERAGE TESTS
# =============================================================================

def test_generate_api_key_format():
    """Test API key generation format."""
    from app.auth.services.api_keys import generate_api_key, hash_api_key, ALLOWED_SCOPES
    
    key = generate_api_key()
    assert key.startswith("fk_")
    # Should be fk_ + uuid4 (36 chars with dashes)
    parts = key.split("_")
    assert len(parts) == 2
    assert len(parts[1]) == 36  # UUID with dashes
    # Should be valid UUID format
    uuid.UUID(parts[1])
    
    # Test hashing
    hash_val = hash_api_key(key)
    assert len(hash_val) == 64  # SHA-256 hex
    assert all(c in "0123456789abcdef" for c in hash_val)


def test_validate_scopes_read_only():
    """Test validate_scopes only allows read scopes."""
    from app.auth.services.api_keys import validate_scopes, ALLOWED_SCOPES
    
    # Valid read scopes - should not raise
    validate_scopes(["read:models"])
    validate_scopes(["read:categories"])
    validate_scopes(["read:providers"])
    validate_scopes(["read:locales"])
    validate_scopes(["read:models", "read:categories"])
    
    # Write scopes should raise ValueError
    with pytest.raises(ValueError):
        validate_scopes(["write:models"])
    with pytest.raises(ValueError):
        validate_scopes(["read:models", "write:categories"])
    with pytest.raises(ValueError):
        validate_scopes(["delete:models"])
    with pytest.raises(ValueError):
        validate_scopes(["admin:all"])
    
    # Unknown scopes rejected
    with pytest.raises(ValueError):
        validate_scopes(["unknown:scope"])


def test_validate_rate_limit():
    """Test rate limit validation."""
    from app.auth.services.api_keys import validate_rate_limit
    
    # Valid limits
    validate_rate_limit(1)
    validate_rate_limit(60)
    validate_rate_limit(500)
    validate_rate_limit(300)
    
    # Invalid limits
    with pytest.raises(ValueError):
        validate_rate_limit(0)
    with pytest.raises(ValueError):
        validate_rate_limit(-1)
    with pytest.raises(ValueError):
        validate_rate_limit(501)
    with pytest.raises(ValueError):
        validate_rate_limit(1000)
    with pytest.raises(ValueError):
        validate_rate_limit("60")  # not int


@pytest.mark.asyncio
async def test_api_key_check_rate_limit():
    """Test API key rate limit checking."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    
    redis_dict = {}
    key_hash = hashlib.sha256(b"test-key").hexdigest()
    limit = 60
    
    # First 60 should succeed
    for _ in range(60):
        is_limited, remaining, retry_after = await api_key_check({}, key_hash, 60)
        assert is_limited is False
    
    # 61st should be limited
    is_limited, remaining, retry_after = await api_key_check({}, key_hash, 60)
    assert is_limited is True
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_api_key_check_with_fake_redis():
    """Test API key rate limit with FakeRedis."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    key_hash = hashlib.sha256(b"test-key-2").hexdigest()
    limit = 10
    
    # First 10 should succeed
    for _ in range(limit):
        is_limited, remaining, retry_after = await api_key_check(fake_redis, key_hash, limit)
        assert is_limited is False
    
    # 11th should be limited
    is_limited, remaining, retry_after = await api_key_check(fake_redis, key_hash, limit)
    assert is_limited is True
    assert retry_after > 0


def test_hash_api_key():
    """Test hash_api_key produces consistent SHA-256."""
    from app.auth.services.api_keys import hash_api_key
    
    key = "fk_abcdef1234567890abcdef1234567890"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)
    
    assert hash1 == hash2
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)


def test_validate_scopes():
    """Test validate_scopes raises ValueError on invalid scopes."""
    from app.auth.services.api_keys import validate_scopes, ALLOWED_SCOPES
    
    # Valid read scopes - should not raise
    validate_scopes(["read:models"])
    validate_scopes(["read:categories"])
    validate_scopes(["read:providers"])
    validate_scopes(["read:locales"])
    validate_scopes(["read:models", "read:categories"])
    
    # Write scopes should raise ValueError
    with pytest.raises(ValueError):
        validate_scopes(["write:models"])
    with pytest.raises(ValueError):
        validate_scopes(["read:models", "write:categories"])
    with pytest.raises(ValueError):
        validate_scopes(["delete:models"])
    with pytest.raises(ValueError):
        validate_scopes(["admin:all"])
    
    # Unknown scopes rejected
    with pytest.raises(ValueError):
        validate_scopes(["unknown:scope"])
    with pytest.raises(ValueError):
        validate_scopes(["read:unknown"])
    
    # Case sensitivity
    with pytest.raises(ValueError):
        validate_scopes(["Read:models"])
    with pytest.raises(ValueError):
        validate_scopes(["READ:MODELS"])


def test_validate_rate_limit():
    """Test rate limit validation."""
    from app.auth.services.api_keys import validate_rate_limit
    
    # Valid limits
    validate_rate_limit(1)
    validate_rate_limit(60)
    validate_rate_limit(500)
    validate_rate_limit(300)
    
    # Invalid limits
    with pytest.raises(ValueError):
        validate_rate_limit(0)
    with pytest.raises(ValueError):
        validate_rate_limit(-1)
    with pytest.raises(ValueError):
        validate_rate_limit(501)
    with pytest.raises(ValueError):
        validate_rate_limit(1000)
    with pytest.raises(ValueError):
        validate_rate_limit("60")  # not int


@pytest.mark.asyncio
async def test_api_key_check_rate_limit():
    """Test API key rate limit checking."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    
    key_hash = hashlib.sha256(b"test-key").hexdigest()
    limit = 60
    
    # Use a single dict for all calls (simulates Redis)
    redis_dict = {}
    
    # First 60 should succeed
    for _ in range(limit):
        is_limited, remaining, retry_after = await api_key_check(redis_dict, key_hash, limit)
        assert is_limited is False
    
    # 61st should be limited
    is_limited, remaining, retry_after = await api_key_check(redis_dict, key_hash, limit)
    assert is_limited is True
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_api_key_check_with_fake_redis():
    """Test API key rate limit with FakeRedis."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    key_hash = hashlib.sha256(b"test-key-2").hexdigest()
    limit = 10
    
    # First 10 should succeed
    for _ in range(limit):
        is_limited, remaining, retry_after = await api_key_check(fake_redis, key_hash, limit)
        assert is_limited is False
    
    # 11th should be limited
    is_limited, remaining, retry_after = await api_key_check(fake_redis, key_hash, limit)
    assert is_limited is True
    assert retry_after > 0


def test_hash_api_key():
    """Test hash_api_key produces consistent SHA-256."""
    from app.auth.services.api_keys import hash_api_key
    
    key = "fk_abcdef1234567890abcdef1234567890"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)
    
    assert hash1 == hash2
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)


def test_validate_scopes():
    """Test validate_scopes raises ValueError on invalid scopes."""
    from app.auth.services.api_keys import validate_scopes, ALLOWED_SCOPES
    
    # Valid read scopes - should not raise
    validate_scopes(["read:models"])
    validate_scopes(["read:categories"])
    validate_scopes(["read:providers"])
    validate_scopes(["read:locales"])
    validate_scopes(["read:models", "read:categories"])
    
    # Write scopes should raise ValueError
    with pytest.raises(ValueError):
        validate_scopes(["write:models"])
    with pytest.raises(ValueError):
        validate_scopes(["read:models", "write:categories"])
    with pytest.raises(ValueError):
        validate_scopes(["delete:models"])
    with pytest.raises(ValueError):
        validate_scopes(["admin:all"])
    
    # Unknown scopes rejected
    with pytest.raises(ValueError):
        validate_scopes(["unknown:scope"])
    with pytest.raises(ValueError):
        validate_scopes(["read:unknown"])
    
    # Case sensitivity
    with pytest.raises(ValueError):
        validate_scopes(["Read:models"])
    with pytest.raises(ValueError):
        validate_scopes(["READ:MODELS"])


def test_validate_rate_limit():
    """Test rate limit validation."""
    from app.auth.services.api_keys import validate_rate_limit
    
    # Valid limits
    validate_rate_limit(1)
    validate_rate_limit(60)
    validate_rate_limit(500)
    validate_rate_limit(300)
    
    # Invalid limits
    with pytest.raises(ValueError):
        validate_rate_limit(0)
    with pytest.raises(ValueError):
        validate_rate_limit(-1)
    with pytest.raises(ValueError):
        validate_rate_limit(501)
    with pytest.raises(ValueError):
        validate_rate_limit(1000)
    with pytest.raises(ValueError):
        validate_rate_limit("60")  # not int


@pytest.mark.asyncio
async def test_api_key_check_rate_limit():
    """Test API key rate limit checking."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    
    key_hash = hashlib.sha256(b"test-key").hexdigest()
    limit = 60
    
    # Use a single dict for all calls (simulates Redis)
    redis_dict = {}
    
    # First 60 should succeed
    for _ in range(limit):
        is_limited, remaining, retry_after = await api_key_check(redis_dict, key_hash, limit)
        assert is_limited is False
    
    # 61st should be limited
    is_limited, remaining, retry_after = await api_key_check(redis_dict, key_hash, limit)
    assert is_limited is True
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_api_key_check_with_fake_redis():
    """Test API key rate limit with FakeRedis."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    key_hash = hashlib.sha256(b"test-key-2").hexdigest()
    limit = 10
    
    # First 10 should succeed
    for _ in range(limit):
        is_limited, remaining, retry_after = await api_key_check(fake_redis, key_hash, limit)
        assert is_limited is False
    
    # 11th should be limited
    is_limited, remaining, retry_after = await api_key_check(fake_redis, key_hash, limit)
    assert is_limited is True
    assert retry_after > 0


def test_hash_api_key():
    """Test hash_api_key produces consistent SHA-256."""
    from app.auth.services.api_keys import hash_api_key
    
    key = "fk_abcdef1234567890abcdef1234567890"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)
    
    assert hash1 == hash2
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)


def test_validate_scopes():
    """Test validate_scopes raises ValueError on invalid scopes."""
    from app.auth.services.api_keys import validate_scopes, ALLOWED_SCOPES
    
    # Valid read scopes - should not raise
    validate_scopes(["read:models"])
    validate_scopes(["read:categories"])
    validate_scopes(["read:providers"])
    validate_scopes(["read:locales"])
    validate_scopes(["read:models", "read:categories"])
    
    # Write scopes should raise ValueError
    with pytest.raises(ValueError):
        validate_scopes(["write:models"])
    with pytest.raises(ValueError):
        validate_scopes(["read:models", "write:categories"])
    with pytest.raises(ValueError):
        validate_scopes(["delete:models"])
    with pytest.raises(ValueError):
        validate_scopes(["admin:all"])
    
    # Unknown scopes rejected
    with pytest.raises(ValueError):
        validate_scopes(["unknown:scope"])
    with pytest.raises(ValueError):
        validate_scopes(["read:unknown"])
    
    # Case sensitivity
    with pytest.raises(ValueError):
        validate_scopes(["Read:models"])
    with pytest.raises(ValueError):
        validate_scopes(["READ:MODELS"])


def test_validate_rate_limit():
    """Test rate limit validation."""
    from app.auth.services.api_keys import validate_rate_limit
    
    # Valid limits
    validate_rate_limit(1)
    validate_rate_limit(60)
    validate_rate_limit(500)
    validate_rate_limit(300)
    
    # Invalid limits
    with pytest.raises(ValueError):
        validate_rate_limit(0)
    with pytest.raises(ValueError):
        validate_rate_limit(-1)
    with pytest.raises(ValueError):
        validate_rate_limit(501)
    with pytest.raises(ValueError):
        validate_rate_limit(1000)
    with pytest.raises(ValueError):
        validate_rate_limit("60")  # not int


def test_api_key_schemas():
    """Test API key Pydantic schemas validation."""
    from app.auth.schemas.api_keys import APIKeyCreate, APIKeyRead, APIKeyCreateResponse
    
    # Valid create
    create = APIKeyCreate(name="Test Key", scopes=["read:models"], rate_limit_rpm=100)
    assert create.name == "Test Key"
    assert create.scopes == ["read:models"]
    assert create.rate_limit_rpm == 100
    
    # Default rate limit
    create2 = APIKeyCreate(name="Default", scopes=["read:models"])
    assert create2.rate_limit_rpm == 60
    
    # Invalid rate limit
    with pytest.raises(Exception):
        APIKeyCreate(name="Bad", scopes=["read:models"], rate_limit_rpm=0)
    
    with pytest.raises(Exception):
        APIKeyCreate(name="Bad", scopes=["read:models"], rate_limit_rpm=501)
    
    # Write scope rejected
    with pytest.raises(Exception):
        APIKeyCreate(name="Write", scopes=["write:models"])
    
    # Frozen
    create3 = APIKeyCreate(name="Frozen", scopes=["read:models"])
    with pytest.raises(Exception):
        create3.name = "hacked"  # type: ignore


def test_api_key_read_schema():
    """Test APIKeyRead schema."""
    from app.auth.schemas.api_keys import APIKeyRead
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    read = APIKeyRead(
        id=str(uuid.uuid4()),
        name="Test",
        scopes=["read:models"],
        rate_limit_rpm=60,
        created_at=datetime.now(timezone.utc),
        revoked_at=None
    )
    assert read.name == "Test"
    assert read.revoked_at is None
    
    # Frozen
    with pytest.raises(Exception):
        read.name = "hacked"  # type: ignore


def test_api_key_create_response_schema():
    """Test APIKeyCreateResponse includes full key once."""
    from app.auth.schemas.api_keys import APIKeyCreateResponse
    
    response = APIKeyCreateResponse(
        id=str(uuid.uuid4()),
        name="Test",
        scopes=["read:models"],
        rate_limit_rpm=60,
        key="fk_abcdef1234567890abcdef1234567890",
        created_at=datetime.now(timezone.utc)
    )
    assert response.key.startswith("fk_")
    assert len(response.key) == 3 + 32  # fk_ + 32 hex chars
    
    # Frozen
    with pytest.raises(Exception):
        response.key = "hacked"  # type: ignore


def test_api_key_list_schema():
    """Test APIKeyList schema."""
    from app.auth.schemas.api_keys import APIKeyList, APIKeyRead
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    item = APIKeyRead(
        id=str(uuid.uuid4()),
        name="Test",
        scopes=["read:models"],
        rate_limit_rpm=60,
        created_at=datetime.now(timezone.utc),
        updated_at=now,
        revoked_at=None
    )
    lst = APIKeyList(data=[item], total=1)
    assert lst.total == 1
    assert len(lst.data) == 1