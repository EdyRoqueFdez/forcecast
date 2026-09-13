"""Phase 6 Middleware RBAC — TDD tests for get_current_user, require_admin, require_api_key, public exemptions, composability."""

import uuid
import hashlib
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.auth.services.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_jti,
)
from app.auth.models.user import User, RoleEnum
from app.auth.models.api_key import APIKey
from app.auth.middleware.auth import (
    get_current_user,
    require_admin,
    require_api_key,
    get_redis,
    set_redis,
    # New symbols for 6.4/6.5 — these must exist (RED → GREEN)
    PUBLIC_ENDPOINTS,
    AUTH_EXEMPT_ENDPOINTS,
    is_public_path,
    get_current_user_or_api_key,
)
from app.db.session import get_session, Base
from app.main import app


# Helper to create test engine/session
def make_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:")


def make_session_factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def engine_and_session():
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_session_factory(engine)
    yield engine, factory
    await engine.dispose()


# ---------------------------------------------------------------------------
# 6.1 get_current_user — JWT via cookie/header + revocation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_valid_cookie_token(engine_and_session):
    """Valid access_token cookie must return User."""
    engine, factory = engine_and_session
    async with factory() as db:
        user = User(email="cookie@example.com", display_name="CookieUser", email_verified=True, role=RoleEnum.USER)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)

    token = create_access_token(user_id=user_id, role="user")
    fake_redis = {}
    # patch get_redis for auth middleware
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        # Also patch jwt service redis check — get_redis is used inside auth.py
        scope = {"type": "http", "headers": [], "cookies": {}}
        # Build Request with cookie
        from fastapi import Request as FastAPIRequest
        # httpx-style: use Starlette Request with headers containing cookie header
        headers = [(b"cookie", f"access_token={token}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        # Need DB session
        async with factory() as db2:
            result = await get_current_user(request, db2)
            assert result.email == "cookie@example.com"
            assert str(result.id) == user_id

    # triangulation: second user with different email must also work
    async with factory() as db:
        user2 = User(email="cookie2@example.com", display_name="Cookie2", email_verified=True)
        db.add(user2)
        await db.commit()
        await db.refresh(user2)
        user2_id = str(user2.id)
    token2 = create_access_token(user_id=user2_id, role="user")
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"cookie", f"access_token={token2}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db2:
            result2 = await get_current_user(request, db2)
            assert result2.email == "cookie2@example.com"


@pytest.mark.asyncio
async def test_valid_bearer_token(engine_and_session):
    """Valid Authorization Bearer header must return User."""
    engine, factory = engine_and_session
    async with factory() as db:
        user = User(email="bearer@example.com", display_name="Bearer", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)
    token = create_access_token(user_id=user_id, role="user")
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"authorization", f"Bearer {token}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db2:
            result = await get_current_user(request, db2)
            assert result.email == "bearer@example.com"


@pytest.mark.asyncio
async def test_expired_token(engine_and_session):
    """Expired JWT must raise 401 token expired."""
    engine, factory = engine_and_session
    user_id = str(uuid.uuid4())
    # create expired token
    expired = create_access_token(user_id=user_id, role="user", expires_delta=timedelta(seconds=-10))
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"authorization", f"Bearer {expired}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db:
            with pytest.raises(HTTPException) as exc:
                await get_current_user(request, db)
            assert exc.value.status_code == 401
            assert "expired" in exc.value.detail.lower()

    # triangulation: different expired token also rejected
    expired2 = create_access_token(user_id=str(uuid.uuid4()), role="admin", expires_delta=timedelta(seconds=-5))
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"cookie", f"access_token={expired2}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db:
            with pytest.raises(HTTPException) as exc:
                await get_current_user(request, db)
            assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_revoked_token(engine_and_session):
    """Revoked JTI must raise 401 token revoked."""
    engine, factory = engine_and_session
    async with factory() as db:
        user = User(email="revoked@example.com", display_name="RevokedUser", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)
    token = create_access_token(user_id=user_id, role="user")
    payload = decode_token(token)
    jti = payload["jti"]
    fake_redis = {}
    await revoke_jti(fake_redis, jti, ttl_seconds=1800)
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"authorization", f"Bearer {token}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db:
            with pytest.raises(HTTPException) as exc:
                await get_current_user(request, db)
            assert exc.value.status_code == 401
            assert "revoked" in exc.value.detail.lower()

    # triangulation: non-revoked token for same user must pass
    token2 = create_access_token(user_id=user_id, role="user")
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"authorization", f"Bearer {token2}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db:
            result = await get_current_user(request, db)
            assert str(result.id) == user_id


@pytest.mark.asyncio
async def test_missing_token_raises_401(engine_and_session):
    """Missing token must raise 401."""
    engine, factory = engine_and_session
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db:
            with pytest.raises(HTTPException) as exc:
                await get_current_user(request, db)
            assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# 6.2 require_admin
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_access(engine_and_session):
    """Admin user must pass require_admin."""
    engine, factory = engine_and_session
    async with factory() as db:
        admin = User(email="admin@example.com", display_name="Admin", role=RoleEnum.ADMIN, email_verified=True)
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        admin_id = str(admin.id)
    token = create_access_token(user_id=admin_id, role="admin")
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"authorization", f"Bearer {token}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db:
            # require_admin depends on get_current_user → simulate by calling get_current_user first then require_admin
            user = await get_current_user(request, db)
            result = await require_admin(user)
            assert result.role.value == "admin" if hasattr(result.role, "value") else str(result.role) == "admin"


@pytest.mark.asyncio
async def test_user_denied(engine_and_session):
    """Non-admin user must get 403 on require_admin."""
    engine, factory = engine_and_session
    async with factory() as db:
        user = User(email="user@example.com", display_name="User", role=RoleEnum.USER, email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)
    token = create_access_token(user_id=user_id, role="user")
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"authorization", f"Bearer {token}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        async with factory() as db:
            user_obj = await get_current_user(request, db)
            with pytest.raises(HTTPException) as exc:
                await require_admin(user_obj)
            assert exc.value.status_code == 403
            assert "admin" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# 6.3 require_api_key — valid and revoked
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_valid_api_key(engine_and_session):
    """Valid X-Forcecast-Api-Key must return User and set read-only context."""
    engine, factory = engine_and_session
    async with factory() as db:
        user = User(email="apikey-valid@example.com", display_name="ApiValid", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)
        # create API key
        from app.auth.services.api_keys import generate_api_key, hash_api_key
        plain = generate_api_key()
        hashed = hash_api_key(plain)
        api_key_row = APIKey(id=str(uuid.uuid4()), user_id=user_id, name="test-key", key_hash=hashed, scopes=["read:models"], rate_limit_rpm=60)
        db.add(api_key_row)
        await db.commit()
        api_key_value = plain
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"x-forcecast-api-key", api_key_value.encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        # Need Response object to capture headers
        response = Response()
        async with factory() as db:
            result = await require_api_key(request, db, response)
            assert str(result.id) == user_id
            assert getattr(request.state, "is_api_key", False) is True
            assert "read:models" in getattr(request.state, "api_key_scopes", [])

    # triangulation: second key with different scope must also work
    async with factory() as db:
        from app.auth.services.api_keys import generate_api_key, hash_api_key
        plain2 = generate_api_key()
        hashed2 = hash_api_key(plain2)
        row2 = APIKey(id=str(uuid.uuid4()), user_id=user_id, name="key2", key_hash=hashed2, scopes=["read:categories"], rate_limit_rpm=60)
        db.add(row2)
        await db.commit()
        val2 = plain2
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"x-forcecast-api-key", val2.encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        response = Response()
        async with factory() as db:
            result2 = await require_api_key(request, db, response)
            assert str(result2.id) == user_id
            assert "read:categories" in getattr(request.state, "api_key_scopes", [])


@pytest.mark.asyncio
async def test_revoked_api_key(engine_and_session):
    """Revoked API key must raise 401 API key revoked."""
    engine, factory = engine_and_session
    async with factory() as db:
        user = User(email="apikey-revoked@example.com", display_name="ApiRevoked", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)
        from app.auth.services.api_keys import generate_api_key, hash_api_key
        from datetime import datetime, timezone
        plain = generate_api_key()
        hashed = hash_api_key(plain)
        row = APIKey(id=str(uuid.uuid4()), user_id=user_id, name="revoked-key", key_hash=hashed, scopes=["read:models"], rate_limit_rpm=60, revoked_at=datetime.now(timezone.utc))
        db.add(row)
        await db.commit()
        revoked_val = plain
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"x-forcecast-api-key", revoked_val.encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        response = Response()
        async with factory() as db:
            with pytest.raises(HTTPException) as exc:
                await require_api_key(request, db, response)
            assert exc.value.status_code == 401
            assert "revoked" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# 6.4 Public endpoint exemptions
# ---------------------------------------------------------------------------
def test_public_endpoints_constant():
    """PUBLIC_ENDPOINTS must contain required public routes."""
    assert isinstance(PUBLIC_ENDPOINTS, (list, tuple, set))
    public_str = " ".join(PUBLIC_ENDPOINTS)
    for endpoint in ["/api/v1/models", "/api/v1/categories", "/api/v1/providers", "/api/v1/locales", "/health"]:
        assert endpoint in public_str, f"missing public endpoint {endpoint}"
    # OAuth exempt also considered public
    assert any("oauth" in p.lower() or "login" in p.lower() for p in PUBLIC_ENDPOINTS) or any("/auth/login" in p for p in PUBLIC_ENDPOINTS)


def test_auth_exempt_endpoints_constant():
    """AUTH_EXEMPT_ENDPOINTS must list auth routes exempt from admin."""
    assert isinstance(AUTH_EXEMPT_ENDPOINTS, (list, tuple, set))
    auth_str = " ".join(AUTH_EXEMPT_ENDPOINTS)
    for ep in ["/auth/login", "/auth/refresh", "/auth/logout"]:
        assert ep in auth_str, f"missing auth exempt {ep}"


def test_is_public_path():
    """is_public_path must correctly classify public vs protected."""
    # public GET examples
    assert is_public_path("/api/v1/models", method="GET") is True
    assert is_public_path("/api/v1/models/compare", method="GET") is True
    assert is_public_path("/api/v1/categories", method="GET") is True
    assert is_public_path("/api/v1/providers", method="GET") is True
    assert is_public_path("/api/v1/locales", method="GET") is True
    assert is_public_path("/health", method="GET") is True
    assert is_public_path("/.well-known/jwks.json", method="GET") is True
    assert is_public_path("/auth/login/google", method="GET") is True
    assert is_public_path("/auth/callback/google", method="GET") is True
    # triangulation: protected must be False
    assert is_public_path("/api/v1/votes", method="POST") is False
    assert is_public_path("/auth/api-keys", method="POST") is False
    assert is_public_path("/admin/users", method="GET") is False


@pytest.mark.asyncio
async def test_public_endpoint_no_auth():
    """GET /api/v1/models without auth must succeed (public)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        # ensure not 401
        assert resp.status_code != 401

    # triangulation: other public GETs also succeed
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ["/api/v1/categories", "/api/v1/providers", "/health"]:
            resp = await client.get(path)
            assert resp.status_code == 200, f"{path} should be public, got {resp.status_code}"


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth():
    """POST /auth/api-keys without auth must return 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/auth/api-keys", json={"name": "x", "scopes": ["read:models"]})
        assert resp.status_code == 401

    # triangulation: GET /auth/me without auth also 401
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/me")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_endpoints_exempt():
    """Auth endpoints like /auth/refresh without admin token must NOT return 403 (rate-limited, not admin-blocked)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # /auth/refresh with no token → 401 (auth required) but NOT 403 admin
        resp = await client.post("/auth/refresh", json={})
        assert resp.status_code in (401, 422)  # 401 missing token, 422 body parse, but not 403
        assert resp.status_code != 403
        # /.well-known/jwks.json is public
        resp2 = await client.get("/.well-known/jwks.json")
        assert resp2.status_code == 200
        assert "keys" in resp2.json()


# ---------------------------------------------------------------------------
# 6.5 Middleware composability — dual auth JWT OR API key
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dual_auth_jwt(engine_and_session):
    """Dual auth endpoint must accept valid JWT."""
    engine, factory = engine_and_session
    async with factory() as db:
        user = User(email="dual-jwt@example.com", display_name="DualJWT", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)
    token = create_access_token(user_id=user_id, role="user")
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"authorization", f"Bearer {token}".encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        response = Response()
        async with factory() as db:
            result = await get_current_user_or_api_key(request, db, response)
            assert str(result.id) == user_id


@pytest.mark.asyncio
async def test_dual_auth_api_key(engine_and_session):
    """Dual auth endpoint must accept valid API key when JWT missing."""
    engine, factory = engine_and_session
    async with factory() as db:
        user = User(email="dual-apikey@example.com", display_name="DualKey", email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)
        from app.auth.services.api_keys import generate_api_key, hash_api_key
        plain = generate_api_key()
        hashed = hash_api_key(plain)
        row = APIKey(id=str(uuid.uuid4()), user_id=user_id, name="dual-key", key_hash=hashed, scopes=["read:models"], rate_limit_rpm=60)
        db.add(row)
        await db.commit()
        plain_val = plain
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        headers = [(b"x-forcecast-api-key", plain_val.encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        response = Response()
        async with factory() as db:
            result = await get_current_user_or_api_key(request, db, response)
            assert str(result.id) == user_id
            assert getattr(request.state, "is_api_key", False) is True

    # triangulation: also via integration test GET /auth/me with API key should work
    # Create fresh DB for integration via overridden dependency
    engine2 = make_engine()
    async with engine2.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory2 = make_session_factory(engine2)
    async with factory2() as db:
        user2 = User(email="dual-int@example.com", display_name="DualInt", email_verified=True)
        db.add(user2)
        await db.commit()
        await db.refresh(user2)
        uid2 = str(user2.id)
        from app.auth.services.api_keys import generate_api_key, hash_api_key
        plain2 = generate_api_key()
        hashed2 = hash_api_key(plain2)
        row2 = APIKey(id=str(uuid.uuid4()), user_id=uid2, name="dual2", key_hash=hashed2, scopes=["read:models"], rate_limit_rpm=60)
        db.add(row2)
        await db.commit()
        plain2_val = plain2
        jwt2 = create_access_token(user_id=uid2, role="user")

    async def override_get_session():
        async with factory2() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # JWT path
        resp_jwt = await client.get("/auth/me", headers={"Authorization": f"Bearer {jwt2}"})
        assert resp_jwt.status_code == 200
        assert resp_jwt.json().get("email") == "dual-int@example.com"
        # API key fallback
        resp_key = await client.get("/auth/me", headers={"X-Forcecast-Api-Key": plain2_val})
        assert resp_key.status_code == 200
        assert resp_key.json().get("email") == "dual-int@example.com"
    app.dependency_overrides.clear()
    await engine2.dispose()


@pytest.mark.asyncio
async def test_dual_auth_missing_both_raises_401(engine_and_session):
    """Dual auth with no JWT nor API key must raise 401."""
    engine, factory = engine_and_session
    fake_redis = {}
    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "server": ("testserver", 80), "scheme": "http"}
        request = Request(scope)
        response = Response()
        async with factory() as db:
            with pytest.raises(HTTPException) as exc:
                await get_current_user_or_api_key(request, db, response)
            assert exc.value.status_code == 401
