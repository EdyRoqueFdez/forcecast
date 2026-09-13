"""Additional coverage tests for uncovered branches in anti_bot.py"""

import hashlib
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.auth.services.anti_bot import (
    generate_fingerprint,
    generate_fingerprint_from_request,
    verify_turnstile,
    get_effective_rate_limit,
    is_strict_mode,
    adjust_reputation,
    check_fingerprint_mismatch,
    check_rapid_account_creation,
    record_account_creation,
    check_refresh_anomaly,
    clear_anti_bot_state,
    STRICT_THRESHOLD,
    REPUTATION_PENALTY,
)
from app.auth.models.user import User, RoleEnum


class FakeRequest:
    """Mock FastAPI Request object."""
    def __init__(self, ua="", ip="", lang="", xff=None):
        self.headers = {}
        if ua:
            self.headers["user-agent"] = ua
        if lang:
            self.headers["accept-language"] = lang
        if xff:
            self.headers["x-forwarded-for"] = xff
        self.client = MagicMock()
        self.client.host = ip


class FakeSession:
    def __init__(self, fp="", created_at=None):
        self.device_fingerprint = fp
        self.created_at = created_at
        self.last_active_at = created_at


def test_fingerprint_from_request():
    """Test generate_fingerprint_from_request extracts from request correctly."""
    # Clear state
    from app.auth.services.anti_bot import clear_anti_bot_state
    clear_anti_bot_state()
    
    # Test with x-forwarded-for
    req = FakeRequest(ua="Mozilla/5.0 Chrome", ip="1.2.3.4", lang="en-US", xff="10.0.0.1, 192.168.1.1")
    fp = generate_fingerprint_from_request(req)
    assert isinstance(fp, str)
    assert len(fp) == 64
    
    # Should use first IP from x-forwarded-for
    # The implementation takes first IP from x-forwarded-for
    req2 = FakeRequest(ua="Mozilla/5.0 Firefox", ip="5.6.7.8", lang="fr-FR", xff="203.0.113.5")
    fp2 = generate_fingerprint_from_request(req2)
    assert isinstance(fp2, str)
    assert len(fp2) == 64
    assert fp != fp2  # Different IP should give different fingerprint
    
    # Test with no x-forwarded-for (falls back to client.host)
    req3 = FakeRequest(ua="Mozilla/5.0 Safari", ip="9.9.9.9", lang="de-DE")
    fp3 = generate_fingerprint_from_request(req3)
    assert len(fp3) == 64
    
    # Test error handling - missing headers
    class EmptyRequest:
        def __init__(self):
            self.headers = {}
            self.client = None
    
    empty_req = EmptyRequest()
    fp_empty = generate_fingerprint_from_request(empty_req)
    assert len(fp_empty) == 64  # Should not crash, returns hash of "unknown"


@pytest.mark.asyncio
async def test_verify_turnstile_network_error():
    """Test verify_turnstile handles network errors gracefully."""
    from app.auth.services.anti_bot import verify_turnstile, clear_anti_bot_state
    from app.auth.services import anti_bot
    
    anti_bot.clear_anti_bot_state()
    
    # Test network timeout exception
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=Exception("network timeout"))
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await verify_turnstile("any-token", remote_ip="1.2.3.4")
        assert result is False
    
    # Test connection error
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=ConnectionError("connection refused"))
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await verify_turnstile("any-token", remote_ip="1.2.3.4")
        assert result is False
    
    # Test invalid JSON response
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("invalid json")
        mock_response.status_code = 200
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await verify_turnstile("any-token")
        assert result is False


@pytest.mark.asyncio
async def test_verify_turnstile_no_secret():
    """Test verify_turnstile when no secret configured."""
    from app.auth.services.anti_bot import verify_turnstile, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    # When no secret, should still attempt verification but mock determines result
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True}
    mock_response.status_code = 200
    
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await verify_turnstile("valid-token")
        # Should return True based on mocked response
        assert result is True


def test_adjust_reputation_clamping():
    """Test adjust_reputation clamps at 0.0 and 10.0."""
    from app.auth.services.anti_bot import adjust_reputation, clear_anti_bot_state
    from app.auth.services import anti_bot
    from app.auth.models.user import User
    
    anti_bot.clear_anti_bot_state()
    
    user = User(email="clamp@example.com", display_name="Clamp", email_verified=True)
    user.reputation_score = 5.0
    
    # Test upper clamp at 10.0
    for i in range(100):
        adjust_reputation(user, 0.1)
    assert user.reputation_score <= 10.0
    assert user.reputation_score == 10.0
    
    # Test lower clamp at 0.0
    user.reputation_score = 0.0
    for i in range(100):
        adjust_reputation(user, -0.1)
    assert user.reputation_score >= 0.0
    assert user.reputation_score == 0.0
    
    # Test exact boundary
    user.reputation_score = 0.05
    adjust_reputation(user, -0.1)
    assert user.reputation_score == 0.0
    
    user.reputation_score = 9.95
    adjust_reputation(user, 0.1)
    assert user.reputation_score == 10.0


def test_adjust_reputation_none_score():
    """Test adjust_reputation handles None reputation_score."""
    from app.auth.services.anti_bot import adjust_reputation, clear_anti_bot_state
    from app.auth.services import anti_bot
    from app.auth.models.user import User
    
    anti_bot.clear_anti_bot_state()
    
    user = User(email="none_score@example.com", display_name="NoneScore", email_verified=True)
    # reputation_score is None initially (before flush)
    assert user.reputation_score is None
    
    # Should treat None as 5.0 and apply delta
    new_score = adjust_reputation(user, -0.1)
    assert new_score == 4.9
    
    user2 = User(email="none2@example.com", display_name="None2", email_verified=True)
    new_score2 = adjust_reputation(user2, 1.0)
    assert new_score2 == 6.0


@pytest.mark.asyncio
async def test_check_fingerprint_mismatch_no_stored():
    """Test check_fingerprint_mismatch when no stored fingerprint."""
    from app.auth.services.anti_bot import check_fingerprint_mismatch, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    user = User(email="nomatch@example.com", display_name="NoMatch", email_verified=True)
    user.reputation_score = 5.0
    user.id = str(uuid.uuid4())
    
    result = await check_fingerprint_mismatch(
        session_fingerprint=None,
        current_fingerprint="some_fingerprint",
        user=user
    )
    
    assert result["mismatch"] is False
    assert result["anomaly"] is False
    assert result["reason"] == "no stored fingerprint"
    assert result["reputation_after"] == 5.0


@pytest.mark.asyncio
async def test_check_fingerprint_mismatch_match():
    """Test fingerprint match returns no anomaly."""
    from app.auth.services.anti_bot import check_fingerprint_mismatch, generate_fingerprint, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    ua = "Mozilla/5.0 Chrome"
    ip = "1.2.3.4"
    lang = "en-US"
    fp = generate_fingerprint(ua, ip, lang)
    
    user = User(email="match@example.com", display_name="Match", email_verified=True)
    user.reputation_score = 5.0
    user.id = str(uuid.uuid4())
    
    result = await check_fingerprint_mismatch(
        session_fingerprint=fp,
        current_fingerprint=fp,
        user=user
    )
    
    assert result["mismatch"] is False
    assert result["anomaly"] is False
    assert result["reason"] == "match"
    assert result["reputation_after"] == 5.0
    assert user.reputation_score == 5.0  # No penalty


@pytest.mark.asyncio
async def test_check_fingerprint_mismatch_strict_mode():
    """Test fingerprint mismatch in strict mode logs warning."""
    from app.auth.services.anti_bot import check_fingerprint_mismatch, generate_fingerprint, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    fp1 = generate_fingerprint("Mozilla/5.0 Chrome", "1.2.3.4", "en-US")
    fp2 = generate_fingerprint("Mozilla/5.0 Firefox", "5.6.7.8", "fr-FR")
    
    user = User(email="strict@example.com", display_name="Strict", email_verified=True)
    user.reputation_score = 2.5  # Below threshold -> strict mode
    user.id = str(uuid.uuid4())
    
    # Should not raise, just log warning
    result = await check_fingerprint_mismatch(
        session_fingerprint="old_fp",
        current_fingerprint="new_fp",
        user=user
    )
    
    assert result["mismatch"] is True
    assert result["anomaly"] is True
    assert user.reputation_score < 5.0


def test_is_strict_mode_edge_cases():
    """Test is_strict_mode with various user configurations."""
    from app.auth.services.anti_bot import is_strict_mode, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    # User with None reputation_score (treated as 5.0)
    user_none = User(email="none@example.com", display_name="None", email_verified=True)
    assert is_strict_mode(user_none) is False
    
    # User with 0 reputation
    user_zero = User(email="zero@example.com", display_name="Zero", email_verified=True)
    user_zero.reputation_score = 0.0
    assert is_strict_mode(user_zero) is True
    
    # User with exactly 3.0 (boundary)
    user_boundary = User(email="boundary@example.com", display_name="Boundary", email_verified=True)
    user_boundary.reputation_score = 3.0
    assert is_strict_mode(user_boundary) is False
    
    # User with 2.999 (below threshold)
    user_below = User(email="below@example.com", display_name="Below", email_verified=True)
    user_below.reputation_score = 2.999
    assert is_strict_mode(user_below) is True
    
    # Admin with low reputation still strict
    from app.auth.models.user import RoleEnum
    admin_low = User(email="adminlow@example.com", display_name="AdminLow", role=RoleEnum.ADMIN, email_verified=True)
    admin_low.reputation_score = 2.0
    assert is_strict_mode(admin_low) is True


def test_get_effective_rate_limit_various_roles():
    """Test get_effective_rate_limit with various role configurations."""
    from app.auth.services.anti_bot import get_effective_rate_limit, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    from app.auth.models.user import RoleEnum
    
    # Normal user
    user = User(email="normal@example.com", display_name="Normal", email_verified=True)
    user.reputation_score = 5.0
    assert get_effective_rate_limit(user) == 300
    
    # Admin
    admin = User(email="admin2@example.com", display_name="Admin2", role=RoleEnum.ADMIN, email_verified=True)
    admin.reputation_score = 5.0
    assert get_effective_rate_limit(admin) == 1000
    
    # Low rep normal user
    low_user = User(email="lowrate@example.com", display_name="LowRate", email_verified=True)
    low_user.reputation_score = 2.0
    assert get_effective_rate_limit(low_user) == 150
    
    # Low rep admin
    low_admin = User(email="lowadmin2@example.com", display_name="LowAdmin2", role=RoleEnum.ADMIN, email_verified=True)
    low_admin.reputation_score = 2.0
    assert get_effective_rate_limit(low_admin) == 500
    
    # Edge case: role is string not enum
    user_str_role = User(email="strrole@example.com", display_name="StrRole", email_verified=True)
    user_str_role.reputation_score = 5.0
    user_str_role.role = "admin"  # string instead of enum
    assert get_effective_rate_limit(user_str_role) == 1000


@pytest.mark.asyncio
async def test_record_account_creation_edge_cases():
    """Test record_account_creation with various redis types."""
    from app.auth.services.anti_bot import record_account_creation, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    # Test with dict redis
    redis_dict = {}
    ip = "192.168.100.1"
    
    cnt1 = await record_account_creation(ip, redis_dict)
    assert cnt1 == 1
    
    cnt2 = await record_account_creation(ip, redis_dict)
    assert cnt2 == 2
    
    # Test with FakeRedis-like object (has .store)
    class FakeRedis:
        def __init__(self):
            self.store = {}
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    cnt3 = await record_account_creation("10.0.0.1", fake_redis)
    assert cnt3 == 1
    
    # Test window cleaning - old timestamps removed
    import time
    from app.auth.services.anti_bot import record_account_creation, clear_anti_bot_state, _rapid_creation_buckets
    
    clear_anti_bot_state()
    
    # Manually add old timestamp
    key = "rapid_acct:10.0.0.2"
    _rapid_creation_buckets[key] = [time.time() - 700]  # 700 seconds ago (outside 600s window)
    
    cnt = await record_account_creation("10.0.0.2", {})
    assert cnt == 1  # Old timestamp should be cleaned


@pytest.mark.asyncio
async def test_check_rapid_account_creation_edge_cases():
    """Test check_rapid_account_creation with various scenarios."""
    from app.auth.services.anti_bot import check_rapid_account_creation, record_account_creation, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    redis_dict = {}
    ip = "198.51.100.1"
    
    # Under limit
    for i in range(4):
        await record_account_creation(ip, redis_dict)
        blocked = await check_rapid_account_creation(ip, redis_dict)
        assert blocked is False
    
    # 5th creation - at limit but not blocked yet
    await record_account_creation(ip, redis_dict)
    blocked = await check_rapid_account_creation(ip, redis_dict)
    assert blocked is False
    
    # 6th - blocked
    await record_account_creation(ip, redis_dict)
    blocked = await check_rapid_account_creation(ip, redis_dict)
    assert blocked is True
    
    # Different IP not blocked
    assert await check_rapid_account_creation("192.0.2.1", redis_dict) is False
    
    # Test with FakeRedis (has .store attribute)
    class FakeRedis:
        def __init__(self):
            self.store = {}
    
    fake = type('FakeRedis', (), {'store': {}})()
    await record_account_creation("198.51.100.2", fake)
    blocked = await check_rapid_account_creation("198.51.100.2", fake)
    assert blocked is False


@pytest.mark.asyncio
async def test_check_refresh_anomaly_no_stored_fp():
    """Test check_refresh_anomaly when session has no stored fingerprint."""
    from app.auth.services.anti_bot import check_refresh_anomaly, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    from datetime import datetime, timezone, timedelta
    
    class FakeSession:
        def __init__(self):
            self.device_fingerprint = None
            self.created_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    
    user = User(email="nofp@example.com", display_name="NoFP", email_verified=True)
    user.id = str(uuid.uuid4())
    user.reputation_score = 5.0
    
    session = FakeSession()
    result = await check_refresh_anomaly(
        session=FakeSession(),
        new_fingerprint="some_fingerprint",
        user=user
    )
    
    assert result["anomaly"] is False
    assert result["reason"] == "no stored fingerprint"


@pytest.mark.asyncio
async def test_check_refresh_anomaly_match_same_device():
    """Test refresh anomaly with matching fingerprint (no anomaly)."""
    from app.auth.services.anti_bot import check_refresh_anomaly, generate_fingerprint, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    from datetime import datetime, timezone, timedelta
    
    fp = generate_fingerprint("Mozilla/5.0 Chrome", "1.1.1.1", "en-US")
    
    class FakeSession:
        def __init__(self, fp):
            self.device_fingerprint = fp
            self.created_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    
    user = User(email="samedevice@example.com", display_name="Same", email_verified=True)
    user.id = str(uuid.uuid4())
    user.reputation_score = 5.0
    
    fp = generate_fingerprint("Mozilla/5.0 Chrome", "1.1.1.1", "en-US")
    
    session = FakeSession(fp)
    result = await check_refresh_anomaly(
        session=type('obj', (object,), {'device_fingerprint': fp, 'created_at': datetime.now(timezone.utc) - timedelta(minutes=1)})(),
        new_fingerprint=fp,
        user=user
    )
    
    assert result["anomaly"] is False
    assert user.reputation_score == 5.0


@pytest.mark.asyncio
async def test_check_refresh_anomaly_old_session():
    """Test refresh anomaly with session older than 5 minutes."""
    from app.auth.services.anti_bot import check_refresh_anomaly, generate_fingerprint, clear_anti_bot_state
    
    clear_anti_bot_state()
    
    from datetime import datetime, timezone, timedelta
    
    fp_original = generate_fingerprint("Mozilla/5.0 Chrome", "1.1.1.1", "en-US")
    fp_new = generate_fingerprint("Mozilla/5.0 Safari", "2.2.2.2", "en-US")
    
    class FakeSession:
        def __init__(self, fp, created_at):
            self.device_fingerprint = fp
            self.created_at = created_at
    
    user = User(email="oldsess@example.com", display_name="OldSess", email_verified=True)
    user.id = str(uuid.uuid4())
    user.reputation_score = 5.0
    
    # Session created 10 minutes ago - older than 5min threshold
    session = type('obj', (object,), {
        'device_fingerprint': fp_original,
        'created_at': datetime.now(timezone.utc) - timedelta(minutes=10)
    })()
    
    result = await check_refresh_anomaly(
        session=session,
        new_fingerprint=fp_new,
        user=user
    )
    
    # Session older than 5min -> no anomaly even with different fingerprint
    assert result["anomaly"] is False


def test_clear_anti_bot_state():
    """Test clear_anti_bot_state resets global state."""
    from app.auth.services.anti_bot import clear_anti_bot_state, _rapid_creation_buckets, _reputation_log
    
    # Add some state
    import app.auth.services.anti_bot as ab
    ab._rapid_creation_buckets["test"] = [time.time()]
    ab._reputation_log.append({"test": "data"})
    
    clear_anti_bot_state()
    
    assert len(ab._rapid_creation_buckets) == 0
    assert len(ab._reputation_log) == 0