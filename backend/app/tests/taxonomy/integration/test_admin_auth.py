"""Phase 6.2 — Admin Auth + Rate Limit (TDD RED)"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, Request, Response
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_session
from app.auth.services.jwt import create_access_token
from app.taxonomy.api.dependencies import require_admin, RateLimiter
from app.core.config import settings


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")

    @sa_event.listens_for(eng.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with eng.begin() as conn:
        await conn.execute(sa_text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def admin_token(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.auth.models.user import User, RoleEnum
        import uuid

        user = User(
            id=str(uuid.uuid4()),
            email="admin@test.com",
            display_name="Admin",
            role=RoleEnum.ADMIN,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        token = create_access_token(str(user.id), "admin")
        # Return token and user id
        yield token, str(user.id)


@pytest_asyncio.fixture
async def user_token(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.auth.models.user import User, RoleEnum
        import uuid

        user = User(
            id=str(uuid.uuid4()),
            email="user@test.com",
            display_name="User",
            role=RoleEnum.USER,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        token = create_access_token(str(user.id), "user")
        yield token


def make_app(engine):
    app = FastAPI()

    # Simple protected endpoint using require_admin
    @app.get("/admin/protected")
    async def protected(user=Depends(require_admin), request: Request = None, response: Response = None):
        # RateLimiter should be applied as dependency too — but we test separately
        return {"user_id": str(user.id), "role": str(user.role.value) if hasattr(user.role, "value") else str(user.role)}

    # Endpoint with rate limiting
    limiter = RateLimiter(requests_per_minute=5)

    @app.get("/admin/rate-limited")
    async def rate_limited(request: Request, response: Response, user=Depends(require_admin), _rl=Depends(limiter)):
        return {"ok": True}

    # Override get_session to use engine
    async def override_get_session():
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    return app


@pytest.mark.asyncio
async def test_jwt_admin_success(engine, admin_token):
    token, _ = admin_token
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/admin/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_missing_auth_returns_401(engine):
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/admin/protected")
    assert resp.status_code == 401
    # spec expects error.code UNAUTHORIZED or detail indicates 401
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_non_admin_role_returns_403(engine, user_token):
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/admin/protected", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_key_admin_prefix_success(engine):
    # Create user + api key with fk_admin_ prefix
    from app.auth.models.api_key import APIKey
    from app.auth.models.user import User, RoleEnum
    import hashlib
    import uuid

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="apikey_admin@test.com",
            display_name="API Admin",
            role=RoleEnum.ADMIN,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        raw_key = f"fk_admin_{uuid.uuid4().hex}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = APIKey(
            id=str(uuid.uuid4()),
            user_id=user.id,
            key_hash=key_hash,
            name="test",
            scopes=["read:models"],
            rate_limit_rpm=1000,
        )
        s.add(api_key)
        await s.commit()
        adm_key = raw_key

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/admin/protected", headers={"X-Forcecast-Api-Key": adm_key})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_headers_present(engine, admin_token):
    token, _ = admin_token
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/admin/rate-limited", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 429)
    # Headers must include rate limit info on success
    # On 200, headers include X-RateLimit-*
    if resp.status_code == 200:
        assert "X-RateLimit-Limit" in resp.headers or "X-Rate-Limit-Limit" in resp.headers or "x-ratelimit-limit" in {k.lower(): v for k, v in resp.headers.items()}
        # check at least one variant present
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}
        assert "x-ratelimit-limit" in headers_lower
        assert "x-ratelimit-remaining" in headers_lower
        assert "x-ratelimit-reset" in headers_lower


@pytest.mark.asyncio
async def test_rate_limit_429_with_retry_after(engine, admin_token):
    token, _ = admin_token
    app = make_app(engine)
    # need to override limiter to very low for test — we used 5/min above, so hammer 6 times
    client = TestClient(app)
    last_resp = None
    for _ in range(7):
        last_resp = client.get("/admin/rate-limited", headers={"Authorization": f"Bearer {token}"})
    assert last_resp is not None
    # After 5 allowed, 6th or 7th should be 429
    assert last_resp.status_code == 429
    headers_lower = {k.lower(): v for k, v in last_resp.headers.items()}
    assert "retry-after" in headers_lower
