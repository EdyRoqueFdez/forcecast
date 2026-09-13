"""Phase 7 Integration — TDD RED tests (must FAIL until implementation exists).

Covers 7.1 taxonomy admin protection, 7.2 router wiring, 7.3 seed, 7.4 E2E, 7.5 OpenAPI contract.
Strict TDD: tests written FIRST, then implementation.
"""

import uuid
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.auth.services.jwt import create_access_token, create_refresh_token, decode_token, revoke_jti, verify_token
from app.auth.models.user import User, RoleEnum
from app.db.session import Base, get_session
from app.main import app


def make_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:")


def make_factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# 7.1 Taxonomy admin protection
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_access_taxonomy():
    """Admin JWT must access POST /api/v1/admin/models/{id}/approve."""
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_factory(engine)

    async with factory() as db:
        admin = User(email="admin-tax@example.com", display_name="AdminTax", role=RoleEnum.ADMIN, email_verified=True)
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        admin_id = str(admin.id)

    token = create_access_token(user_id=admin_id, role="admin")
    fake_redis = {}

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override

    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 7.1 expects POST /api/v1/admin/models/{id}/approve to exist and succeed for admin
            resp = await client.post(f"/api/v1/admin/models/{uuid.uuid4()}/approve", headers={"Authorization": f"Bearer {token}"})
            # Should be 200 (approved) or 404 if model not found but NOT 401/403
            assert resp.status_code in (200, 201, 404, 422)  # 404 acceptable if no model, but must NOT be auth error
            assert resp.status_code not in (401, 403), f"admin should be authorized, got {resp.status_code} {resp.text}"

            # triangulation: another admin endpoint
            resp2 = await client.post("/api/v1/admin/ingestion/run", json={"source": "openrouter"}, headers={"Authorization": f"Bearer {token}"})
            assert resp2.status_code not in (401, 403), f"admin ingestion should be authorized, got {resp2.status_code}"

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_blocked_taxonomy():
    """Non-admin JWT must get 403 on POST /api/v1/admin/*."""
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_factory(engine)

    async with factory() as db:
        user = User(email="user-tax@example.com", display_name="UserTax", role=RoleEnum.USER, email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)

    token = create_access_token(user_id=user_id, role="user")
    fake_redis = {}

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override

    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/v1/admin/models/{uuid.uuid4()}/approve", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403
            assert "admin" in resp.text.lower()

            resp2 = await client.post("/api/v1/admin/ingestion/run", json={"source": "openrouter"}, headers={"Authorization": f"Bearer {token}"})
            assert resp2.status_code == 403

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_unauth_blocked_taxonomy():
    """No auth header must get 401 on POST /api/v1/admin/webhooks."""
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_factory(engine)

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/admin/webhooks", json={"url": "https://example.com/hook", "events": ["model.approved"], "secret": "s"})
        assert resp.status_code == 401

        # triangulation: other admin endpoint without auth also 401
        resp2 = await client.post(f"/api/v1/admin/models/{uuid.uuid4()}/approve")
        assert resp2.status_code == 401

    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# 7.2 Wire auth routers in main.py
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_routes_registered():
    """All auth endpoints must be registered in OpenAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        paths = spec.get("paths", {})

        # OAuth
        assert "/auth/login/{provider}" in paths, "missing /auth/login/{provider}"
        assert "/auth/callback/{provider}" in paths, "missing /auth/callback/{provider}"
        # Tokens
        assert "/auth/refresh" in paths, "missing /auth/refresh"
        assert "/auth/logout" in paths, "missing /auth/logout"
        assert "/.well-known/jwks.json" in paths, "missing JWKS"
        # API keys
        assert "/auth/api-keys" in paths, "missing POST /auth/api-keys"
        # Admin (taxonomy)
        assert "/api/v1/admin/models/{id}/approve" in paths or any("/api/v1/admin" in p for p in paths), "missing admin routes"
        # Health still public
        assert "/health" in paths

        # CORS check: allow-credentials header present on auth request?
        # We check that docs accessible
        resp2 = await client.get("/docs")
        assert resp2.status_code == 200


# ---------------------------------------------------------------------------
# 7.3 Seed data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_seeded():
    """Seed must create admin@forcecast.dev with role=admin, email_verified=true."""
    from app.db.seed import seed_admin

    engine = make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_factory(engine)

    async with factory() as db:
        await seed_admin(db)
        await db.commit()
        result = await db.execute(select(User).where(User.email == "admin@forcecast.dev"))
        admin = result.scalars().first()
        assert admin is not None, "admin user not seeded"
        role_val = admin.role.value if hasattr(admin.role, "value") else str(admin.role)
        assert role_val == "admin"
        assert admin.email_verified is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_idempotent():
    """Seed must be idempotent — no duplicate on re-run."""
    from app.db.seed import seed_admin

    engine = make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_factory(engine)

    async with factory() as db:
        await seed_admin(db)
        await db.commit()
        await seed_admin(db)
        await db.commit()
        result = await db.execute(select(User).where(User.email == "admin@forcecast.dev"))
        admins = result.scalars().all()
        assert len(admins) == 1, f"seed not idempotent, found {len(admins)} admins"

        # triangulation: add second seed still 1
        await seed_admin(db)
        await db.commit()
        result2 = await db.execute(select(User).where(User.email == "admin@forcecast.dev"))
        assert len(result2.scalars().all()) == 1

    await engine.dispose()


# ---------------------------------------------------------------------------
# 7.4 E2E integration tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_full_auth_flow():
    """OAuth login → protected access → refresh → logout → verify revoked (E2E)."""
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_factory(engine)

    # Simulate OAuth login: create user via find_or_create_user logic
    from app.auth.services.oauth import find_or_create_user

    async with factory() as db:
        profile = {"email": "e2e@example.com", "name": "E2E User", "picture": None}
        user = await find_or_create_user(db, "google", profile)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)

        # Create session
        from app.auth.models.session import Session
        sess = Session(user_id=user.id, ip_address="127.0.0.1", user_agent="pytest-e2e")
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        session_id = str(sess.id)

    fake_redis = {}

    # Create token pair (as OAuth callback would via jwt service)
    access = create_access_token(user_id=user_id, role="user")
    refresh = create_refresh_token(user_id=user_id, session_id=session_id)

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override

    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis), \
         patch("app.auth.api.tokens.get_redis", return_value=fake_redis):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Protected access: GET /auth/me with access token
            resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
            assert resp.status_code == 200
            assert resp.json().get("email") == "e2e@example.com"

            # Refresh
            resp2 = await client.post("/auth/refresh", json={"refresh_token": refresh})
            assert resp2.status_code == 200
            data = resp2.json()
            assert "access_token" in data
            assert "refresh_token" in data
            new_access = data["access_token"]
            new_refresh = data["refresh_token"]
            # old refresh revoked
            payload_old = decode_token(refresh)
            assert await verify_token(new_access, fake_redis) is not None  # new valid
            # old revoked check via is_jti_revoked
            from app.auth.services.jwt import is_jti_revoked
            assert await is_jti_revoked(fake_redis, payload_old["jti"]) is True

            # New token can access protected
            resp3 = await client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
            assert resp3.status_code == 200

            # Logout with new refresh (and access)
            resp4 = await client.post("/auth/logout", json={"refresh_token": new_refresh, "access_token": new_access}, headers={"Authorization": f"Bearer {new_access}"})
            assert resp4.status_code == 200
            # After logout, new_access should be revoked
            with pytest.raises(Exception):
                await verify_token(new_access, fake_redis)

            # Verify revoked: attempt protected with revoked token
            resp5 = await client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
            assert resp5.status_code == 401

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_post_logout_denied():
    """Post-logout token must be rejected with 401."""
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = make_factory(engine)

    async with factory() as db:
        user = User(email="postlogout@example.com", display_name="PostLogout", email_verified=True, role=RoleEnum.USER)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = str(user.id)
        from app.auth.models.session import Session
        sess = Session(user_id=user.id, ip_address="10.0.0.1", user_agent="pytest")
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        session_id = str(sess.id)

    fake_redis = {}
    access = create_access_token(user_id=user_id, role="user")
    refresh = create_refresh_token(user_id=user_id, session_id=session_id)

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override

    with patch("app.auth.middleware.auth.get_redis", return_value=fake_redis), \
         patch("app.auth.api.tokens.get_redis", return_value=fake_redis):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Logout
            resp = await client.post("/auth/logout", json={"refresh_token": refresh, "access_token": access})
            assert resp.status_code == 200

            # Revoked access should fail
            resp2 = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
            assert resp2.status_code == 401

            # Revoked refresh should fail on refresh
            resp3 = await client.post("/auth/refresh", json={"refresh_token": refresh})
            assert resp3.status_code == 401

            # triangulation: different user's valid token still works (not blanket revoke)
            async with factory() as db:
                other = User(email="other@example.com", display_name="Other", email_verified=True)
                db.add(other)
                await db.commit()
                await db.refresh(other)
                other_id = str(other.id)
            other_token = create_access_token(user_id=other_id, role="user")
            resp4 = await client.get("/auth/me", headers={"Authorization": f"Bearer {other_token}"})
            assert resp4.status_code == 200

    app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# 7.5 Contract testing — OpenAPI schema
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_openapi_contract():
    """OpenAPI schema must match auth contract expectations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec.get("openapi", "").startswith("3.")
        paths = spec["paths"]

        # Auth endpoints shape
        expected = [
            ("/auth/login/{provider}", "get"),
            ("/auth/callback/{provider}", "get"),
            ("/auth/refresh", "post"),
            ("/auth/logout", "post"),
            ("/.well-known/jwks.json", "get"),
            ("/auth/api-keys", "post"),
            ("/auth/api-keys", "get"),
            ("/auth/api-keys/{key_id}", "delete"),
            ("/auth/me", "get"),
        ]
        for path, method in expected:
            assert path in paths, f"missing contract path {path}"
            assert method in paths[path], f"path {path} missing method {method}"
            # Check responses defined
            assert "responses" in paths[path][method]

        # Admin endpoints in contract
        admin_paths = [p for p in paths if p.startswith("/api/v1/admin")]
        assert len(admin_paths) >= 3, f"expected at least 3 admin paths, got {admin_paths}"
        # Ensure security scheme hint? openapi may have security via dependencies — check that at least 401 documented
        for p in admin_paths:
            for method_spec in paths[p].values():
                assert "responses" in method_spec

        # JWKS shape validation (via live endpoint)
        jwks_resp = await client.get("/.well-known/jwks.json")
        assert jwks_resp.status_code == 200
        jwks = jwks_resp.json()
        assert "keys" in jwks
        assert jwks["keys"][0]["kty"] == "RSA"

        # Triangulation: ensure auth error response schema consistent
        auth_error = paths.get("/auth/error", {})
        if auth_error:
            assert "get" in auth_error
