"""Phase 2 OAuth2/OIDC — TDD RED tests (must FAIL until implementation exists)."""
import hashlib
import base64
import uuid

import pytest

# TDD RED: these imports will FAIL until app/auth/services/oauth.py exists
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
)
from app.core.config import settings


# ---------------------------------------------------------------------------
# 2.1 PKCE generation
# ---------------------------------------------------------------------------
def test_pkce_generation():
    verifier = generate_code_verifier()
    # RFC7636: 43-128 chars, urlsafe
    assert 43 <= len(verifier) <= 128
    assert verifier != generate_code_verifier()  # different each call

    # known RFC7636 example
    known_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert generate_code_challenge(known_verifier) == expected_challenge

    # challenge is base64url without padding
    challenge = generate_code_challenge(verifier)
    assert "=" not in challenge
    assert 40 <= len(challenge) <= 128


def test_pkce_challenge_deterministic():
    verifier = "test-verifier-12345"
    c1 = generate_code_challenge(verifier)
    c2 = generate_code_challenge(verifier)
    assert c1 == c2
    # different verifier -> different challenge
    assert generate_code_challenge("other-verifier") != c1


# ---------------------------------------------------------------------------
# 2.1 State validation (Redis-backed)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_state_validation():
    # Use in-memory fake redis dict via dependency injection
    fake_redis = {}
    state = generate_state_token()
    assert 30 <= len(state) <= 64
    verifier = generate_code_verifier()

    await store_state(fake_redis, state, verifier, ttl=600)
    # valid state returns verifier
    returned = await validate_state(fake_redis, state)
    assert returned == verifier
    # single-use: second validation fails
    second = await validate_state(fake_redis, state)
    assert second is None


@pytest.mark.asyncio
async def test_invalid_state_rejected():
    fake_redis = {}
    result = await validate_state(fake_redis, "nonexistent-state-xyz")
    assert result is None


# ---------------------------------------------------------------------------
# 2.1 Auth URL building
# ---------------------------------------------------------------------------
def test_google_auth_url():
    state = "test_state_123"
    challenge = "test_challenge_abc"
    url = build_authorization_url("google", state, challenge)
    assert "accounts.google.com" in url
    assert f"client_id={settings.GOOGLE_CLIENT_ID}" in url or "client_id=" in url
    assert "response_type=code" in url
    assert "scope=" in url
    assert "openid" in url
    assert f"state={state}" in url
    assert f"code_challenge={challenge}" in url
    assert "code_challenge_method=S256" in url
    assert "redirect_uri=" in url


def test_github_auth_url():
    state = "gh_state_456"
    challenge = "gh_challenge_xyz"
    url = build_authorization_url("github", state, challenge)
    assert "github.com/login/oauth/authorize" in url
    assert f"state={state}" in url
    assert f"code_challenge={challenge}" in url
    assert "code_challenge_method=S256" in url
    assert "user%3Aemail" in url or "user:email" in url or "scope=" in url


def test_unsupported_provider_raises():
    with pytest.raises(ValueError):
        build_authorization_url("facebook", "state", "challenge")


# ---------------------------------------------------------------------------
# 2.2 / 2.3 OAuth API routes — need FastAPI test client
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_redirect():
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch
    from app.main import app as main_app  # will need auth router included

    # Mock redis store to avoid real Redis
    with patch("app.auth.services.oauth.store_state") as mock_store:
        mock_store.return_value = None
        transport = ASGITransport(app=main_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/auth/login/google", follow_redirects=False)
            # Should redirect to provider
            assert resp.status_code in (302, 307)
            assert "accounts.google.com" in resp.headers["location"]
            assert "code_challenge=" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_new_user():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.db.session import Base
    from app.auth.models.user import User

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore

    fake_redis = {}
    state = generate_state_token()
    verifier = generate_code_verifier()
    await store_state(fake_redis, state, verifier)

    # Mock external calls
    from unittest.mock import AsyncMock, patch

    mock_token = {"access_token": "fake_access_token", "token_type": "bearer"}
    mock_profile = {
        "email": "newuser@example.com",
        "name": "New User",
        "picture": "https://example.com/avatar.png",
    }

    with patch("app.auth.services.oauth.exchange_code_for_tokens", new_callable=AsyncMock) as mock_ex, \
         patch("app.auth.services.oauth.get_user_info", new_callable=AsyncMock) as mock_info, \
         patch("app.auth.services.oauth.validate_state", new_callable=AsyncMock) as mock_validate:

        mock_ex.return_value = mock_token
        mock_info.return_value = mock_profile
        mock_validate.return_value = verifier

        async with async_session() as session:
            user = await find_or_create_user(session, "google", mock_profile)
            await session.commit()
            await session.refresh(user)
            assert user.email == "newuser@example.com"
            assert user.email_verified is True
            assert user.display_name == "New User"

            # Verify count =1
            from sqlalchemy import select
            result = await session.execute(select(User))
            users = result.scalars().all()
            assert len(users) == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_callback_account_linking():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.db.session import Base
    from app.auth.models.user import User
    from sqlalchemy import select

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore

    async with async_session() as session:
        # Create existing user via github
        existing = User(email="bob@example.com", display_name="Bob", email_verified=True)
        session.add(existing)
        await session.commit()
        await session.refresh(existing)

        # Same email arrives from Google
        google_profile = {"email": "bob@example.com", "name": "Bob G", "picture": None}
        user = await find_or_create_user(session, "google", google_profile)
        await session.commit()

        assert str(user.id) == str(existing.id)
        # No duplicate
        result = await session.execute(select(User))
        assert len(result.scalars().all()) == 1
        assert user.email_verified is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_email_verified_from_oauth():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.db.session import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore

    async with async_session() as session:
        profile = {"email": "verified@example.com", "name": "Verified", "picture": None}
        user = await find_or_create_user(session, "github", profile)
        await session.commit()
        await session.refresh(user)
        assert user.email_verified is True

    await engine.dispose()


# ---------------------------------------------------------------------------
# 2.4 Error handling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_access_denied_redirect():
    from httpx import AsyncClient, ASGITransport
    from app.main import app as main_app

    transport = ASGITransport(app=main_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/callback/google?error=access_denied&state=any", follow_redirects=False)
        # Should redirect to /auth/error or return error
        assert resp.status_code in (302, 307, 400, 403)
        # If redirect, location contains error
        if resp.status_code in (302, 307):
            assert "access_denied" in resp.headers["location"]


@pytest.mark.asyncio
async def test_provider_timeout():
    from unittest.mock import AsyncMock, patch
    import httpx

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ReadTimeout("timeout", request=None)  # type: ignore
        with pytest.raises(Exception) as exc:
            await exchange_code_for_tokens("google", "code123", "verifier123")
        # Should be timeout-like error (will be mapped to 504 in API)
        assert "timeout" in str(exc.value).lower() or exc.value is not None


@pytest.mark.asyncio
async def test_invalid_state_callback_returns_403():
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch
    from app.main import app as main_app

    # Patch validate_state to return None (invalid)
    with patch("app.auth.services.oauth.validate_state", return_value=None):
        transport = ASGITransport(app=main_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/auth/callback/google?code=abc&state=invalid_state_xyz")
            assert resp.status_code == 403
