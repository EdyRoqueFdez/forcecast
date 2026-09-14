"""Coverage boost for dependencies.py — auth edge cases, rate limiter, IP parsing."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_session
from app.auth.services.jwt import create_access_token
from app.auth.models.user import User, RoleEnum
from app.auth.models.api_key import APIKey
from app.taxonomy.api.dependencies import (
    require_admin,
    RateLimiter,
    clear_rate_limit_state,
    _buckets,
    _get_client_ip,
    _fetch_user_by_id,
)


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


@pytest_asyncio.fixture(autouse=True)
def clear_buckets():
    _buckets.clear()
    yield
    _buckets.clear()


def make_app(engine):
    app = FastAPI()

    async def override_get_session():
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session

    @app.get("/test-admin")
    async def test_admin(user: User = Depends(require_admin)):
        return {"ok": True}

    rl = RateLimiter(requests_per_minute=1000)

    @app.get("/test-admin-rl", dependencies=[Depends(rl)])
    async def test_admin_rl(user: User = Depends(require_admin)):
        return {"ok": True}

    return app


# ---------------------------------------------------------------------------
# Missing auth (line 115)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_auth_returns_401(engine):
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# JWT: expired token (lines 75-83)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_token_returns_401(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="exp@test.com",
            display_name="Exp",
            role=RoleEnum.ADMIN,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        token = create_access_token(str(user.id), "admin", expires_delta=timedelta(seconds=-10))

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# JWT: invalid token with no API key fallback (lines 75-83)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_token_no_api_key_returns_401(engine):
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"Authorization": "Bearer totally-invalid-token"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# JWT: missing sub claim (line 63)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_missing_sub_returns_401(engine):
    from app.auth.services.jwt import _get_private_pem, _get_kid
    import jwt as pyjwt

    token = pyjwt.encode(
        {"role": "admin", "exp": datetime.now(timezone.utc) + timedelta(minutes=30), "iss": "forcecast"},
        _get_private_pem(),
        algorithm="RS256",
        headers={"kid": _get_kid()},
    )
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# JWT: user not found (line 66)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_user_not_found_returns_401(engine):
    fake_id = str(uuid.uuid4())
    token = create_access_token(fake_id, "admin")
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# JWT: non-admin user (line 70)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_admin_user_returns_403(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="regular@test.com",
            display_name="Regular",
            role=RoleEnum.USER,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        token = create_access_token(str(user.id), "user")

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# API key: successful admin auth (line 107)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_key_admin_success(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="keyadmin@test.com",
            display_name="KeyAdmin",
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
            name="adminkey",
            key_hash=key_hash,
            scopes=["admin"],
        )
        s.add(api_key)
        await s.commit()

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"X-Forcecast-Api-Key": raw_key})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# API key: non-admin prefix fk_ (line 91)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_key_non_admin_prefix_returns_403(engine):
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"X-Forcecast-Api-Key": "fk_user_abc123"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# API key: no match in DB (line 113)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_key_no_match_returns_401(engine):
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"X-Forcecast-Api-Key": f"fk_admin_{uuid.uuid4().hex}"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# API key: revoked key (line 100)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_key_revoked_returns_401(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="keyrev@test.com",
            display_name="KeyRev",
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
            name="revoked",
            key_hash=key_hash,
            scopes=["admin"],
            revoked_at=datetime.now(timezone.utc),
        )
        s.add(api_key)
        await s.commit()

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"X-Forcecast-Api-Key": raw_key})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# API key: user not found (line 103) — mock _fetch_user_by_id to return None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_key_user_not_found_returns_401(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="keyorphan@test.com",
            display_name="KeyOrphan",
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
            name="orphan",
            key_hash=key_hash,
            scopes=["admin"],
        )
        s.add(api_key)
        await s.commit()

    app = make_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.api.dependencies._fetch_user_by_id", return_value=None):
        resp = client.get("/test-admin", headers={"X-Forcecast-Api-Key": raw_key})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# API key: non-admin user (line 106)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_key_non_admin_user_returns_403(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="keyuser@test.com",
            display_name="KeyUser",
            role=RoleEnum.USER,
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
            name="userkey",
            key_hash=key_hash,
            scopes=["admin"],
        )
        s.add(api_key)
        await s.commit()

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/test-admin", headers={"X-Forcecast-Api-Key": raw_key})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# _get_client_ip: X-Forwarded-For (line 29) — test via rate limiter endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_xff_header_used_for_client_ip(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="xff@test.com",
            display_name="XFF",
            role=RoleEnum.ADMIN,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        token = create_access_token(str(user.id), "admin")

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get(
        "/test-admin-rl",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Forwarded-For": "1.2.3.4, 5.6.7.8",
        },
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# _get_client_ip: no client info (line 32)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_client_returns_unknown():
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client = None
    result = _get_client_ip(mock_request)
    assert result == "unknown"


# ---------------------------------------------------------------------------
# _fetch_user_by_id: DB exception (lines 39-40)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_user_by_id_db_exception():
    mock_db = MagicMock()
    mock_db.execute.side_effect = RuntimeError("db error")
    result = await _fetch_user_by_id(mock_db, "fake-id")
    assert result is None


# ---------------------------------------------------------------------------
# _fetch_user_by_id exception → user not found (lines 39-40, 66)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_db_exception_during_user_lookup(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="dberr@test.com",
            display_name="DBErr",
            role=RoleEnum.ADMIN,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        token = create_access_token(str(user.id), "admin")

    app = make_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.api.dependencies._fetch_user_by_id", return_value=None):
        resp = client.get("/test-admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# RateLimiter — 429 (lines 135-163)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_429(engine):
    app = FastAPI()

    async def override_get_session():
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session

    rl = RateLimiter(requests_per_minute=2, window=60)

    @app.get("/test-rl-limited", dependencies=[Depends(rl)])
    async def limited_endpoint():
        return {"ok": True}

    client = TestClient(app)
    r1 = client.get("/test-rl-limited")
    assert r1.status_code == 200
    r2 = client.get("/test-rl-limited")
    assert r2.status_code == 200
    r3 = client.get("/test-rl-limited")
    assert r3.status_code == 429
    assert "retry-after" in {h.lower() for h in r3.headers.keys()}


# ---------------------------------------------------------------------------
# clear_rate_limit_state (line 186)
# ---------------------------------------------------------------------------

def test_clear_rate_limit_state():
    _buckets["test_key"] = [1.0, 2.0]
    clear_rate_limit_state()
    assert len(_buckets) == 0
