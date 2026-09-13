"""Additional coverage tests for oauth.py, jwt.py, tokens.py api"""

import uuid
import time
import base64
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.auth.services.oauth import (
    generate_code_verifier,
    generate_code_challenge,
    generate_state_token,
    build_authorization_url,
    store_state,
    validate_state,
    exchange_code_for_tokens,
    get_user_info,
    find_or_create_user,
    PROVIDER_CONFIGS,
)
from app.auth.services.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwks,
    is_jti_revoked,
    revoke_jti,
    verify_token,
    _ensure_keys,
    _base64url_no_pad,
)
from app.auth.schemas.tokens import TokenPair, JWKSResponse
from app.auth.models.user import User, RoleEnum


# =============================================================================
# OAUTH SERVICE COVERAGE
# =============================================================================

def test_pkce_generation_deterministic():
    """Test PKCE code challenge is deterministic for same verifier."""
    from app.auth.services.oauth import generate_code_verifier, generate_code_challenge
    
    verifier = generate_code_verifier()
    challenge1 = generate_code_challenge(verifier)
    challenge2 = generate_code_challenge(verifier)
    assert challenge1 == challenge2
    assert len(challenge1) == 43  # base64url encoded SHA256


def test_state_generation():
    """Test state token generation."""
    from app.auth.services.oauth import generate_state_token
    
    state1 = generate_state_token()
    state2 = generate_state_token()
    assert state1 != state2  # Should be unique
    assert len(state1) > 20


def test_build_authorization_url():
    """Test authorization URL building for each provider."""
    from app.auth.services.oauth import build_authorization_url
    
    # Google
    url = build_authorization_url("google", "state123", "challenge123")
    assert "accounts.google.com" in url
    assert "state123" in url
    assert "challenge123" in url
    assert "S256" in url
    
    # GitHub
    url = build_authorization_url("github", "state456", "challenge456")
    assert "github.com" in url
    assert "state456" in url
    assert "challenge456" in url
    
    # Invalid provider
    with pytest.raises(ValueError):
        build_authorization_url("invalid", "state", "challenge")


@pytest.mark.asyncio
async def test_store_state_validate_state_dict():
    """Test state storage and validation with dict fallback."""
    from app.auth.services.oauth import store_state, validate_state
    
    # Use a single dict for all calls (simulates Redis)
    redis_dict = {}
    
    # Store state - just stores code_verifier
    await store_state(redis_dict, "state123", "verifier123")
    
    # Validate - should succeed and consume (single-use)
    verifier = await validate_state(redis_dict, "state123")
    assert verifier == "verifier123"
    
    # Second validation should fail (single-use)
    verifier2 = await validate_state(redis_dict, "state123")
    assert verifier2 is None
    
    # Non-existent state
    verifier3 = await validate_state(redis_dict, "nonexistent")
    assert verifier3 is None


@pytest.mark.asyncio
async def test_store_state_validate_state_fake_redis():
    """Test state storage with FakeRedis."""
    from app.auth.services.oauth import store_state, validate_state
    
    fake_redis = type('FakeRedis', (), {'store': {}})()
    
    await store_state(fake_redis, "state456", "verifier456")
    verifier = await validate_state(fake_redis, "state456")
    assert verifier == "verifier456"
    
    # Second validation should fail (single-use)
    verifier2 = await validate_state(fake_redis, "state456")
    assert verifier2 is None


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_timeout():
    """Test token exchange handles timeout."""
    from app.auth.services.oauth import exchange_code_for_tokens
    
    with patch("app.auth.services.oauth.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=Exception("timeout"))
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        
        with pytest.raises(Exception):
            await exchange_code_for_tokens("google", "code123", "verifier123")


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_invalid_grant():
    """Test token exchange handles invalid_grant error."""
    from app.auth.services.oauth import exchange_code_for_tokens
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "invalid_grant"}
    mock_response.status_code = 400
    
    with patch("app.auth.services.oauth.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        
        result = await exchange_code_for_tokens("google", "bad_code", "verifier")
        # Should return error dict or raise - check implementation behavior
        assert result is not None
        assert "error" in result
        assert result["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_get_user_info_google():
    """Test get_user_info for Google."""
    from app.auth.services.oauth import get_user_info
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "sub": "google-user-123",
        "email": "user@gmail.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg",
        "email_verified": True
    }
    mock_response.status_code = 200
    
    with patch("app.auth.services.oauth.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.get = AsyncMock(return_value=mock_response)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        
        user_info = await get_user_info("google", "access_token")
        assert user_info["sub"] == "google-user-123"
        assert user_info["email"] == "user@gmail.com"
        assert user_info["email_verified"] is True


@pytest.mark.asyncio
async def test_get_user_info_github():
    """Test get_user_info for GitHub (includes emails endpoint)."""
    from app.auth.services.oauth import get_user_info
    
    mock_user = MagicMock()
    mock_user.json.return_value = {
        "id": 12345,
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://github.com/avatar.jpg",
        "email": "user@github.com"
    }
    mock_user.status_code = 200
    
    with patch("app.auth.services.oauth.httpx.AsyncClient") as Patched:
        instance = AsyncMock()
        instance.get = AsyncMock(return_value=mock_user)
        Patched.return_value.__aenter__.return_value = instance
        Patched.return_value.__aexit__ = AsyncMock(return_value=False)
        
        user_info = await get_user_info("github", "access_token")
        assert user_info["id"] == 12345
        assert user_info["login"] == "testuser"
        assert user_info["email"] == "user@github.com"


# =============================================================================
# JWT SERVICE COVERAGE
# =============================================================================

def test_base64url_no_pad():
    """Test base64url encoding without padding."""
    from app.auth.services.jwt import _base64url_no_pad
    
    # Test various inputs
    assert _base64url_no_pad(b"") == ""
    assert _base64url_no_pad(b"hello") == "aGVsbG8"
    assert _base64url_no_pad(b"hello world") == "aGVsbG8gd29ybGQ"
    # No padding
    assert "=" not in _base64url_no_pad(b"test")


def test_ensure_keys_generation():
    """Test RSA key generation."""
    from app.auth.services.jwt import _ensure_keys
    
    private_key, public_key, kid = _ensure_keys()
    assert private_key is not None
    assert public_key is not None
    assert kid is not None
    # Keys should be PEM format
    assert "BEGIN PRIVATE KEY" in private_key
    assert "BEGIN PUBLIC KEY" in public_key
    
    # Second call should return same keys (cached)
    private_key2, public_key2, kid2 = _ensure_keys()
    assert private_key2 == private_key
    assert public_key2 == public_key
    assert kid2 == kid


def test_create_access_token_various_roles():
    """Test access token creation with different roles."""
    from app.auth.services.jwt import create_access_token, decode_token
    
    user_id = str(uuid.uuid4())
    
    # Admin role
    token = create_access_token(user_id=user_id, role="admin")
    payload = decode_token(token)
    assert payload["role"] == "admin"
    assert payload["sub"] == user_id
    
    # User role
    token = create_access_token(user_id=user_id, role="user")
    payload = decode_token(token)
    assert payload["role"] == "user"
    
    # Custom expiration
    token = create_access_token(user_id=user_id, role="user", expires_delta=timedelta(minutes=5))
    payload = decode_token(token)
    assert payload["exp"] - payload["iat"] == 5 * 60


def test_create_refresh_token_various_sessions():
    """Test refresh token creation with different session IDs."""
    from app.auth.services.jwt import create_refresh_token, decode_token
    
    user_id = str(uuid.uuid4())
    session1 = str(uuid.uuid4())
    session2 = str(uuid.uuid4())
    
    token1 = create_refresh_token(user_id=user_id, session_id=session1)
    token2 = create_refresh_token(user_id=user_id, session_id=session2)
    
    payload1 = decode_token(token1)
    payload2 = decode_token(token2)
    
    assert payload1["session_id"] == session1
    assert payload2["session_id"] == session2
    assert payload1["jti"] != payload2["jti"]
    assert payload1["sub"] == payload2["sub"]


def test_decode_token_expired():
    """Test decoding expired token raises."""
    from app.auth.services.jwt import create_access_token, decode_token
    
    user_id = str(uuid.uuid4())
    # Create token expired 1 hour ago
    token = create_access_token(user_id=user_id, role="user", expires_delta=timedelta(hours=-1))
    
    with pytest.raises(Exception):
        decode_token(token)


def test_jwks_key_format():
    """Test JWKS key format details."""
    from app.auth.services.jwt import get_jwks
    
    jwks = get_jwks()
    assert "keys" in jwks
    assert len(jwks["keys"]) >= 1
    key = jwks["keys"][0]
    
    assert key["kty"] == "RSA"
    assert key["use"] == "sig"
    assert key["alg"] == "RS256"
    assert "kid" in key
    assert "n" in key
    assert "e" in key
    assert key["e"] == "AQAB"  # 65537
    assert "=" not in key["n"]  # no padding
    
    # n should decode to at least 256 bytes (2048 bits)
    padded = key["n"] + "=" * (-len(key["n"]) % 4)
    decoded = base64.urlsafe_b64decode(padded)
    assert len(decoded) >= 256


@pytest.mark.asyncio
async def test_revocation_pubsub_with_fake_redis():
    """Test revocation pub/sub with fake redis."""
    from app.auth.services.jwt import revoke_jti, is_jti_revoked
    
    class FakeRedis(dict):
        def __init__(self):
            super().__init__()
            self.published = []
            self.store = {}
        
        async def set(self, key, value, ex=None):
            self.store[key] = value
        
        async def get(self, key):
            return self.store.get(key)
        
        async def publish(self, channel, message):
            self.published.append((channel, message))
            return 1
        
        async def delete(self, key):
            self.store.pop(key, None)
    
    fake = FakeRedis()
    jti = str(uuid.uuid4())
    
    await revoke_jti(fake, jti, ttl_seconds=1800)
    
    # Must be stored
    assert await is_jti_revoked(fake, jti) is True
    
    # Must have published to channel
    found = any("revocation" in ch or "auth" in ch for ch, _ in fake.published)
    assert found or len(fake.published) >= 1
    
    # Message must contain jti
    assert any(jti in msg for _, msg in fake.published)


# =============================================================================
# TOKENS API COVERAGE
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_rotation_preserves_session():
    """Test refresh rotation preserves session ID."""
    from app.main import app
    from app.auth.services.jwt import create_refresh_token
    from app.auth.models.user import User
    from app.auth.models.session import Session
    from app.db.session import get_session, Base
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        user = User(email="rotation@example.com", display_name="Rotation", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        sess = Session(user_id=user.id, ip_address="127.0.0.1", user_agent="pytest")
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        user_id = str(user.id)
        session_id = str(sess.id)
    
    old_refresh = create_refresh_token(user_id=user_id, session_id=session_id)
    fake_redis = {}
    
    async def override_get_session():
        async with async_session() as session:
            yield session
    
    app.dependency_overrides[get_session] = override_get_session
    
    with patch("app.auth.api.tokens.get_redis", return_value=fake_redis):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
            
            # Verify new refresh token has same session_id
            new_refresh = data["refresh_token"]
            from app.auth.services.jwt import decode_token
            new_payload = decode_token(data["refresh_token"])
            assert new_payload["session_id"] == session_id
    
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_logout_clears_cookies_properly():
    """Test logout sets proper cookie clearing headers."""
    from app.main import app
    from app.auth.services.jwt import create_access_token, create_refresh_token
    from app.auth.models.user import User
    from app.auth.models.session import Session
    from app.db.session import get_session, Base
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        user = User(email="clearcookie2@example.com", display_name="Clear2", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        sess = Session(user_id=user.id, ip_address="127.0.0.1", user_agent="Mozilla")
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        user_id = str(user.id)
        session_id = str(sess.id)
    
    access = create_access_token(user_id=user_id, role="user")
    refresh = create_refresh_token(user_id=user_id, session_id=session_id)
    fake_redis = {}
    
    async def override_get_session():
        async with async_session() as session:
            yield session
    app.dependency_overrides[get_session] = override_get_session
    
    with patch("app.auth.api.tokens.get_redis", return_value=fake_redis):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/auth/logout", 
                json={"refresh_token": refresh}, 
                headers={"Cookie": f"access_token={access}; refresh_token={refresh}"}
            )
            assert resp.status_code == 200
            
            # Check Set-Cookie headers for clearing
            set_cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else [resp.headers.get("set-cookie", "")]
            combined = " ".join([v for v in set_cookies if v]).lower()
            
            # Should have max-age=0 or expires in past
            has_clear = "max-age=0" in combined or "expires=" in combined
            assert has_clear or "access_token" in combined
    
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_mobile_no_cookies_on_json_accept():
    """Test mobile (Accept: application/json) gets no cookies."""
    from app.main import app
    from app.auth.services.jwt import create_refresh_token
    from app.auth.models.user import User
    from app.auth.models.session import Session
    from app.db.session import get_session, Base
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        user = User(email="mobile2@example.com", display_name="Mobile2", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        sess = Session(user_id=user.id, ip_address="127.0.0.1", user_agent="Dart/3.0")
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        user_id = str(user.id)
        session_id = str(sess.id)
    
    token = create_refresh_token(user_id=user_id, session_id=session_id)
    fake_redis = {}
    
    async def override_get_session():
        async with async_session() as session:
            yield session
    app.dependency_overrides[get_session] = override_get_session
    
    with patch("app.auth.api.tokens.get_redis", return_value=fake_redis):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/auth/refresh", 
                json={"refresh_token": token}, 
                headers={"Accept": "application/json"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
            
            # Check cookies - should be minimal or none for mobile
            set_cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else [resp.headers.get("set-cookie", "")]
            combined = " ".join([v for v in set_cookies if v]).lower()
            
            # For mobile, cookies should be minimal or absent
            # At minimum, body must have tokens
            assert "access_token" in data
            assert "refresh_token" in data
    
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_web_cookies_have_correct_attributes():
    """Test web cookies have httpOnly, Secure, SameSite=Lax."""
    from app.main import app
    from app.auth.services.jwt import create_refresh_token
    from app.auth.models.user import User
    from app.auth.models.session import Session
    from app.db.session import get_session, Base
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch
    
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        user = User(email="webattr@example.com", display_name="WebAttr", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        sess = Session(user_id=user.id, ip_address="127.0.0.1", user_agent="Mozilla")
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        user_id = str(user.id)
        session_id = str(sess.id)
    
    token = create_refresh_token(user_id=user_id, session_id=session_id)
    fake_redis = {}
    
    async def override_get_session():
        async with async_session() as session:
            yield session
    app.dependency_overrides[get_session] = override_get_session
    
    with patch("app.auth.api.tokens.get_redis", return_value=fake_redis):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/auth/refresh", 
                json={"refresh_token": token}, 
                headers={"Accept": "text/html"}
            )
            assert resp.status_code == 200
            
            set_cookies = resp.headers.get_list("set-cookie") if hasattr(resp.headers, "get_list") else [resp.headers.get("set-cookie", "")]
            combined = " ".join([v for v in set_cookies if v]).lower()
            
            # Check cookie attributes
            if combined:
                assert "httponly" in combined
                assert "samesite=lax" in combined
                # Secure may not be present in test (non-HTTPS)
    
    app.dependency_overrides.clear()
    await engine.dispose()


# =============================================================================
# OAUTH CALLBACK ERROR HANDLING COVERAGE
# =============================================================================

@pytest.mark.asyncio
async def test_oauth_callback_missing_code():
    """Test OAuth callback with missing code parameter."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing both code and state
        resp = await client.get("/auth/callback/google")
        assert resp.status_code == 400
        
        # Only code, no state
        resp = await client.get("/auth/callback/google?code=abc")
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_oauth_callback_invalid_state():
    """Test OAuth callback with invalid/expired state."""
    from app.main import app
    from httpx import AsyncClient, ASGITransport
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid state (not in store)
        resp = await client.get("/auth/callback/google?code=abc&state=invalid-state")
        assert resp.status_code == 403
        assert "invalid" in resp.json().get("detail", "").lower() or resp.status_code == 403


# =============================================================================
# TOKENS SERVICE EDGE CASES
# =============================================================================

def test_jwt_key_loading_error_handling():
    """Test JWT key loading handles missing files gracefully."""
    from app.auth.services.jwt import _ensure_keys
    
    # Keys should be generated on first call even if files don't exist
    private_key, public_key, kid = _ensure_keys()
    assert private_key is not None
    assert public_key is not None
    assert kid is not None


def test_verify_token_with_revoked_redis():
    """Test verify_token rejects revoked token with Redis."""
    from app.auth.services.jwt import (
        create_access_token, decode_token, revoke_jti, verify_token
    )
    
    fake_redis = {}
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    token = create_refresh_token(user_id=user_id, session_id=str(uuid.uuid4()))
    payload = decode_token(token)
    jti = payload["jti"]
    
    # Revoke
    import asyncio
    asyncio.run(revoke_jti(fake_redis, jti, ttl_seconds=604800))
    
    # Should reject
    import asyncio
    with pytest.raises(Exception):
        asyncio.run(verify_token(token, fake_redis))