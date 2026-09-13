"""Phase 5 Anti-Bot — TDD RED tests (must FAIL until implementation exists)."""

import hashlib
import uuid
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# TDD RED: these imports will FAIL until Phase 5 implementation exists
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
    STRICT_THRESHOLD,
    REPUTATION_PENALTY,
)
from app.auth.middleware.rate_limit import (
    check_rate_limit as check_generic_rate_limit,
    enforce_ip_rate_limit,
    enforce_user_rate_limit,
    LOGIN_IP_LIMIT,
    REGISTER_IP_LIMIT,
    USER_RATE_LIMIT,
    ADMIN_RATE_LIMIT,
)
from app.auth.schemas.anti_bot import TurnstileVerifyRequest, AnomalyEvent
from app.auth.models.user import User, RoleEnum


# ---------------------------------------------------------------------------
# 5.1 anti-bot service — Turnstile, fingerprint, reputation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_turnstile_verification():
    """Valid Turnstile token must verify successfully via provider API."""
    valid_token = "valid-turnstile-token"
    # Mock httpx post to return success
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True}
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aenter__.return_value.__aexit__ = AsyncMock(return_value=False)
        # Simpler: patch verify_turnstile internal httpx call via patch("app.auth.services.anti_bot.httpx.AsyncClient")
        MockClient.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=mock_response)))
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        # Direct patch on httpx used inside verify_turnstile
        with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_response)
            Patched.return_value.__aenter__.return_value = instance
            Patched.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await verify_turnstile(valid_token, remote_ip="1.2.3.4")
            assert result is True

    # triangulation: second valid token also succeeds
    mock_response2 = MagicMock()
    mock_response2.json.return_value = {"success": True}
    mock_response2.status_code = 200
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response2)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        result2 = await verify_turnstile("another-valid-token")
        assert result2 is True


@pytest.mark.asyncio
async def test_invalid_turnstile_rejected():
    """Invalid Turnstile token must be rejected (False or 403 semantics)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": False, "error-codes": ["invalid-input-response"]}
    mock_response.status_code = 200

    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await verify_turnstile("invalid-token", remote_ip="9.9.9.9")
        # Must be False or raise exception with captcha message
        if isinstance(result, bool):
            assert result is False
        else:
            assert False, "should return False or raise"

    # Also test provider error handling — network exception should be treated as False/exception
    with patch("app.auth.services.anti_bot.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=Exception("network timeout"))
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        try:
            result = await verify_turnstile("any-token")
            assert result is False
        except Exception as e:
            assert "captcha" in str(e).lower() or "verification" in str(e).lower() or "failed" in str(e).lower()


def test_fingerprint_generation():
    """Fingerprint must be SHA-256 of UA+IP+Accept-Language, deterministic, 64 hex chars."""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64)"
    ip = "1.2.3.4"
    lang = "en-US,en;q=0.9"

    fp1 = generate_fingerprint(user_agent=ua, ip_address=ip, accept_language=lang)
    assert isinstance(fp1, str)
    assert len(fp1) == 64
    assert all(c in "0123456789abcdef" for c in fp1)
    # deterministic
    fp2 = generate_fingerprint(user_agent=ua, ip_address=ip, accept_language=lang)
    assert fp1 == fp2
    # must equal SHA-256 of concatenated with delimiter (UA|IP|Lang or raw concat)
    # We verify by checking hash of known construction: implementation uses f"{ua}|{ip}|{lang}"
    expected_variants = [
        hashlib.sha256(f"{ua}|{ip}|{lang}".encode()).hexdigest(),
        hashlib.sha256(f"{ua}{ip}{lang}".encode()).hexdigest(),
        hashlib.sha256(f"{ua}:{ip}:{lang}".encode()).hexdigest(),
    ]
    assert fp1 in expected_variants, f"fingerprint {fp1} not in expected variants {expected_variants}"

    # different IP must give different fingerprint
    fp_diff_ip = generate_fingerprint(user_agent=ua, ip_address="5.6.7.8", accept_language=lang)
    assert fp_diff_ip != fp1

    # triangulation: different UA
    fp_diff_ua = generate_fingerprint(user_agent="Firefox/120.0", ip_address=ip, accept_language=lang)
    assert fp_diff_ua != fp1
    assert len(fp_diff_ua) == 64


def test_reputation_initial():
    """New user must start at 5.0 reputation."""
    user = User(email="rep_init@example.com", display_name="RepInit", email_verified=True)
    # SQLAlchemy default is client-side on insert; before flush it may be None — treat None as 5.0
    assert (user.reputation_score or 5.0) == 5.0
    # simulate persisted value for helpers
    if user.reputation_score is None:
        user.reputation_score = 5.0  # type: ignore
    assert not is_strict_mode(user)
    assert get_effective_rate_limit(user) == USER_RATE_LIMIT  # 300 for normal user
    # admin default also 5.0 but limit 1000
    admin = User(email="admin_init@example.com", display_name="AdminInit", role=RoleEnum.ADMIN, email_verified=True)
    if admin.reputation_score is None:
        admin.reputation_score = 5.0  # type: ignore
    assert (admin.reputation_score or 5.0) == 5.0
    assert get_effective_rate_limit(admin) == ADMIN_RATE_LIMIT


def test_reputation_below_threshold():
    """Reputation < 3.0 must halve rate limit and trigger strict mode."""
    assert STRICT_THRESHOLD == 3.0
    low_user = User(email="low@example.com", display_name="Low", email_verified=True)
    low_user.reputation_score = 2.5
    assert is_strict_mode(low_user) is True
    # halved: 300 -> 150
    assert get_effective_rate_limit(low_user) == 150

    low_admin = User(email="lowadmin@example.com", display_name="LowAdmin", role=RoleEnum.ADMIN, email_verified=True)
    low_admin.reputation_score = 2.9
    assert is_strict_mode(low_admin) is True
    assert get_effective_rate_limit(low_admin) == 500  # 1000 halved

    borderline = User(email="border@example.com", display_name="Border", email_verified=True)
    borderline.reputation_score = 3.0
    assert is_strict_mode(borderline) is False
    assert get_effective_rate_limit(borderline) == USER_RATE_LIMIT

    # adjust_reputation must decrement by penalty and clamp 0.0-10.0
    user_for_penalty = User(email="penalty@example.com", display_name="Penalty", email_verified=True)
    user_for_penalty.reputation_score = 5.0
    new_score = adjust_reputation(user_for_penalty, -REPUTATION_PENALTY)
    assert new_score == pytest.approx(4.9)
    assert user_for_penalty.reputation_score == pytest.approx(4.9)

    # clamp at 0.0
    user_for_penalty.reputation_score = 0.05
    adjust_reputation(user_for_penalty, -0.1)
    assert user_for_penalty.reputation_score >= 0.0
    # clamp at 10.0
    user_for_penalty.reputation_score = 9.9
    adjust_reputation(user_for_penalty, 0.5)
    assert user_for_penalty.reputation_score <= 10.0


def test_turnstile_request_schema():
    """TurnstileVerifyRequest schema must validate."""
    req = TurnstileVerifyRequest(token="my-token", remote_ip="1.2.3.4")
    assert req.token == "my-token"
    # empty token should fail validation
    with pytest.raises(Exception):
        TurnstileVerifyRequest(token="", remote_ip="1.2.3.4")
    # frozen
    with pytest.raises(Exception):
        req.token = "hacked"  # type: ignore


def test_anomaly_event_schema():
    """AnomalyEvent schema must capture type and details."""
    evt = AnomalyEvent(type="fingerprint_mismatch", user_id=str(uuid.uuid4()), details={"old": "abc", "new": "xyz"})
    assert evt.type == "fingerprint_mismatch"
    assert "old" in evt.details


# ---------------------------------------------------------------------------
# 5.2 Rate limiter middleware — Redis sliding window, tiers, 429 with Retry-After
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_per_ip_login_limit():
    """Per-IP login limit 10/min: 11th must be limited with Retry-After."""
    redis = {}
    ip = "10.0.0.1"
    # 10 allowed
    for i in range(LOGIN_IP_LIMIT):
        is_limited, remaining, retry_after = await check_generic_rate_limit(redis, f"login:{ip}", LOGIN_IP_LIMIT, window=60)
        assert is_limited is False, f"request {i+1} should not be limited"
    # 11th limited
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis, f"login:{ip}", LOGIN_IP_LIMIT, window=60)
    assert is_limited is True
    assert remaining == 0
    assert retry_after > 0
    assert retry_after <= 60

    # via dependency helper enforce_ip_rate_limit must raise 429 on exceed
    from fastapi import HTTPException
    # Need 6th for register later; for login we already exceed, so enforce should raise
    redis2 = {}

    class FakeRequest:
        def __init__(self, ip):
            self.client = MagicMock(host=ip)
            self.headers = {}
            self.state = MagicMock()

    # Fill redis2 with 10 requests
    for _ in range(LOGIN_IP_LIMIT):
        await check_generic_rate_limit(redis2, f"login:{ip}", LOGIN_IP_LIMIT, window=60)
    fake_req = FakeRequest(ip)
    with pytest.raises(HTTPException) as exc:
        await enforce_ip_rate_limit(fake_req, redis2, endpoint="login")
    assert exc.value.status_code == 429
    assert "retry-after" in {k.lower() for k in (exc.value.headers or {})}


@pytest.mark.asyncio
async def test_per_ip_register_limit():
    """Per-IP register limit 5/min: 6th must be limited."""
    redis = {}
    ip = "10.0.0.2"
    for i in range(REGISTER_IP_LIMIT):
        is_limited, remaining, retry_after = await check_generic_rate_limit(redis, f"register:{ip}", REGISTER_IP_LIMIT, window=60)
        assert is_limited is False
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis, f"register:{ip}", REGISTER_IP_LIMIT, window=60)
    assert is_limited is True
    assert retry_after > 0
    assert remaining == 0


@pytest.mark.asyncio
async def test_per_user_limit():
    """Per-user limit 300/min for normal user: 301st must be limited. Halved to 150 when low reputation."""
    redis = {}
    user = User(email="rate_user@example.com", display_name="RateUser", email_verified=True, role=RoleEnum.USER)
    user.reputation_score = 5.0
    uid = str(uuid.uuid4())
    user.id = uid  # type: ignore
    key = f"user:{uid}"
    # Fill 300
    for _ in range(USER_RATE_LIMIT):
        is_limited, _, _ = await check_generic_rate_limit(redis, key, USER_RATE_LIMIT, window=60)
        assert is_limited is False
    is_limited, remaining, retry_after = await check_generic_rate_limit(redis, key, USER_RATE_LIMIT, window=60)
    assert is_limited is True

    # low reputation halved
    redis2 = {}
    low_user = User(email="low_rate@example.com", display_name="LowRate", email_verified=True)
    low_user.id = str(uuid.uuid4())  # type: ignore
    low_user.reputation_score = 2.0
    effective = get_effective_rate_limit(low_user)
    assert effective == 150
    for _ in range(effective):
        is_limited, _, _ = await check_generic_rate_limit(redis2, f"user:{low_user.id}", effective, window=60)
        assert is_limited is False
    is_limited, _, _ = await check_generic_rate_limit(redis2, f"user:{low_user.id}", effective, window=60)
    assert is_limited is True

    # enforce_user_rate_limit helper
    from fastapi import HTTPException
    redis3 = {}
    for _ in range(USER_RATE_LIMIT):
        await check_generic_rate_limit(redis3, f"user:{uid}", USER_RATE_LIMIT, window=60)

    class FakeRequest:
        def __init__(self):
            self.state = MagicMock()

    fake_req = FakeRequest()
    with pytest.raises(HTTPException) as exc:
        await enforce_user_rate_limit(fake_req, redis3, user=user)
    assert exc.value.status_code == 429
    assert "retry-after" in {k.lower() for k in (exc.value.headers or {})}


@pytest.mark.asyncio
async def test_per_admin_limit():
    """Admin limit 1000/min: 300 must succeed, 1001st blocked; halved to 500 when low rep."""
    redis = {}
    admin = User(email="admin_rate@example.com", display_name="AdminRate", role=RoleEnum.ADMIN, email_verified=True)
    admin.id = str(uuid.uuid4())  # type: ignore
    admin.reputation_score = 5.0
    effective = get_effective_rate_limit(admin)
    assert effective == ADMIN_RATE_LIMIT
    # 300 must succeed for admin
    for _ in range(300):
        is_limited, _, _ = await check_generic_rate_limit(redis, f"user:{admin.id}", effective, window=60)
        assert is_limited is False
    # fill to 1000
    for _ in range(700):
        await check_generic_rate_limit(redis, f"user:{admin.id}", effective, window=60)
    is_limited, _, _ = await check_generic_rate_limit(redis, f"user:{admin.id}", effective, window=60)
    assert is_limited is True

    # low reputation admin halved
    admin.reputation_score = 2.5
    assert get_effective_rate_limit(admin) == 500


@pytest.mark.asyncio
async def test_per_key_limit():
    """Per-key limit (configurable) 60 default, 2 for tiny: 3rd must 429."""
    from app.auth.services.api_keys import check_rate_limit as api_key_check
    redis = {}
    key_hash = hashlib.sha256(b"test-key").hexdigest()
    # tiny limit 2
    for i in range(2):
        is_limited, remaining, retry_after = await api_key_check(redis, key_hash, 2)
        assert is_limited is False
    is_limited, remaining, retry_after = await api_key_check(redis, key_hash, 2)
    assert is_limited is True
    assert retry_after > 0


@pytest.mark.asyncio
async def test_different_ips_independent():
    """Different IPs must have independent rate buckets."""
    redis = {}
    ip_a = "192.168.1.1"
    ip_b = "192.168.1.2"
    # Fill IP_A to limit
    for _ in range(LOGIN_IP_LIMIT):
        await check_generic_rate_limit(redis, f"login:{ip_a}", LOGIN_IP_LIMIT, window=60)
    is_limited_a, _, _ = await check_generic_rate_limit(redis, f"login:{ip_a}", LOGIN_IP_LIMIT, window=60)
    assert is_limited_a is True
    # IP_B should still be allowed (independent)
    is_limited_b, remaining_b, _ = await check_generic_rate_limit(redis, f"login:{ip_b}", LOGIN_IP_LIMIT, window=60)
    assert is_limited_b is False
    assert remaining_b == LOGIN_IP_LIMIT - 1

    # triangulation: third IP also independent
    ip_c = "192.168.1.3"
    is_limited_c, _, _ = await check_generic_rate_limit(redis, f"login:{ip_c}", LOGIN_IP_LIMIT, window=60)
    assert is_limited_c is False


# ---------------------------------------------------------------------------
# 5.3 Anomaly detection — fingerprint drift, velocity, geo impossible (heuristic)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_fingerprint_mismatch_flagged():
    """Fingerprint mismatch must be flagged, anomaly logged, reputation -0.1."""
    user = User(email="drift@example.com", display_name="Drift", email_verified=True)
    user.reputation_score = 5.0
    user.id = str(uuid.uuid4())  # type: ignore
    stored_fp = generate_fingerprint("Mozilla/5.0 Chrome", "1.2.3.4", "en-US")
    new_fp = generate_fingerprint("Mozilla/5.0 Firefox", "5.6.7.8", "fr-FR")
    assert stored_fp != new_fp

    result = await check_fingerprint_mismatch(
        session_fingerprint=stored_fp,
        current_fingerprint=new_fp,
        user=user,
    )
    assert result["mismatch"] is True
    assert result["anomaly"] is True
    # reputation decremented by 0.1
    assert user.reputation_score == pytest.approx(4.9)
    assert "penalty" in result or result.get("reputation_after") == pytest.approx(4.9)

    # matching fingerprint must NOT flag
    user2 = User(email="nodrift@example.com", display_name="NoDrift", email_verified=True)
    user2.reputation_score = 5.0
    user2.id = str(uuid.uuid4())  # type: ignore
    result2 = await check_fingerprint_mismatch(
        session_fingerprint=stored_fp,
        current_fingerprint=stored_fp,
        user=user2,
    )
    assert result2["mismatch"] is False
    assert result2["anomaly"] is False
    assert user2.reputation_score == 5.0


@pytest.mark.asyncio
async def test_rapid_account_creation():
    """5 accounts from same IP in 10min -> 6th must be blocked with 429 semantics."""
    redis = {}
    ip = "203.0.113.5"
    # record 5
    for i in range(5):
        cnt = await record_account_creation(ip, redis)
        assert cnt == i + 1
        blocked = await check_rapid_account_creation(ip, redis)
        assert blocked is False, f"should not be blocked at {i+1}"
    # 6th record
    await record_account_creation(ip, redis)
    blocked = await check_rapid_account_creation(ip, redis)
    assert blocked is True

    # different IP not blocked
    assert await check_rapid_account_creation("203.0.113.6", redis) is False

    # enforce helper must raise 429? via check
    is_blocked = await check_rapid_account_creation(ip, redis)
    assert is_blocked is True


@pytest.mark.asyncio
async def test_refresh_new_device_anomaly():
    """Token refresh from new device within 5min of login must be flagged as anomaly."""
    user = User(email="refresh_anomaly@example.com", display_name="RefreshAnom", email_verified=True)
    user.id = str(uuid.uuid4())  # type: ignore
    user.reputation_score = 5.0
    original_fp = generate_fingerprint("Mozilla/5.0 Chrome", "1.1.1.1", "en-US")
    new_fp = generate_fingerprint("Mozilla/5.0 Safari", "2.2.2.2", "en-US")
    # session created 2 minutes ago
    session_created = datetime.now(timezone.utc) - timedelta(minutes=2)

    class FakeSession:
        def __init__(self, fp, created_at):
            self.device_fingerprint = fp
            self.created_at = created_at
            self.last_active_at = created_at

    sess = FakeSession(original_fp, session_created)
    result = await check_refresh_anomaly(session=sess, new_fingerprint=new_fp, user=user)
    assert result["anomaly"] is True
    assert "new_device" in result.get("reason", "").lower() or "refresh" in result.get("reason", "").lower() or result.get("anomaly") is True
    # reputation penalty?
    assert user.reputation_score == pytest.approx(4.9)

    # triangulation: same device within 5min must NOT flag
    user2 = User(email="refresh_ok@example.com", display_name="RefreshOk", email_verified=True)
    user2.id = str(uuid.uuid4())  # type: ignore
    user2.reputation_score = 5.0
    sess2 = FakeSession(original_fp, session_created)
    result2 = await check_refresh_anomaly(session=sess2, new_fingerprint=original_fp, user=user2)
    assert result2["anomaly"] is False

    # old session (>5min) with new device should also be less strict? But our heuristic says <5min only
    old_created = datetime.now(timezone.utc) - timedelta(minutes=10)
    sess3 = FakeSession(original_fp, old_created)
    user3 = User(email="refresh_old@example.com", display_name="RefreshOld", email_verified=True)
    user3.id = str(uuid.uuid4())  # type: ignore
    user3.reputation_score = 5.0
    result3 = await check_refresh_anomaly(session=sess3, new_fingerprint=new_fp, user=user3)
    # older than 5min, new device is not considered anomaly (or less severe)
    assert result3["anomaly"] is False or result3.get("reason") is not None
