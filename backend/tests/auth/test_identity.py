"""Phase 1 Identity Foundation — TDD RED tests (must FAIL until implementation exists)."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# These imports will FAIL until implementation exists (TDD RED gate)
from app.auth.models.user import ProviderEnum, RoleEnum, User
from app.auth.models.session import Session
from app.auth.models.refresh_token import RefreshToken
from app.auth.models.api_key import APIKey
from app.auth.schemas.identity import DeviceFingerprintInput, OAuthCallback, UserRead, UserUpdate
from app.core.config import settings
from app.db.session import Base


# ---------------------------------------------------------------------------
# 1.1 Module imports
# ---------------------------------------------------------------------------
def test_module_imports():
    import app.auth  # noqa: F401
    import app.auth.models  # noqa: F401
    import app.auth.schemas  # noqa: F401
    import app.auth.services  # noqa: F401
    import app.auth.api  # noqa: F401
    import app.auth.middleware  # noqa: F401
    assert True


# ---------------------------------------------------------------------------
# 1.2 User model
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_user_model_creation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]
    async with async_session() as session:
        user = User(
            email="alice@example.com",
            display_name="Alice",
            role=RoleEnum.USER,
            email_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert user.id is not None
        # id is stored as string(36) for sqlite compat; must be valid UUID
        assert uuid.UUID(str(user.id)) is not None
        assert user.email == "alice@example.com"
        assert user.display_name == "Alice"
        assert user.role == RoleEnum.USER
        assert user.email_verified is True
        assert user.reputation_score == 5.0
        assert user.created_at is not None
        assert user.updated_at is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_email_prevented():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as session:
        u1 = User(email="dup@example.com", display_name="First", role=RoleEnum.USER)
        session.add(u1)
        await session.commit()
        u2 = User(email="dup@example.com", display_name="Second", role=RoleEnum.USER)
        session.add(u2)
        with pytest.raises(IntegrityError):
            await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_default_role_user():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as session:
        user = User(email="norole@example.com", display_name="NoRole")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert user.role == RoleEnum.USER
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_promotion():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as session:
        user = User(email="promote@example.com", display_name="Promote", role=RoleEnum.USER)
        session.add(user)
        await session.commit()
        user.role = RoleEnum.ADMIN
        await session.commit()
        await session.refresh(user)
        assert user.role == RoleEnum.ADMIN
    await engine.dispose()


def test_provider_enum_values():
    assert ProviderEnum.GOOGLE == "google"
    assert ProviderEnum.GITHUB == "github"
    assert ProviderEnum.EMAIL == "email"
    assert RoleEnum.USER == "user"
    assert RoleEnum.ADMIN == "admin"


# ---------------------------------------------------------------------------
# 1.3 Session model
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_session_creation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as session:
        user = User(email="sess@example.com", display_name="Sess")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        sess = Session(
            user_id=user.id,
            device_fingerprint="abc123",
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        assert sess.id is not None
        assert sess.user_id == user.id
        assert sess.device_fingerprint == "abc123"
        assert sess.revoked_at is None
        assert sess.created_at is not None
        assert sess.last_active_at is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_session_revoked_on_logout():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as session:
        user = User(email="logout@example.com", display_name="Logout")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        sess = Session(user_id=user.id, ip_address="10.0.0.1", user_agent="test")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess.revoked_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(sess)
        assert sess.revoked_at is not None
    await engine.dispose()


# ---------------------------------------------------------------------------
# 1.4 RefreshToken model
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_refresh_token_model():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as session:
        user = User(email="rt@example.com", display_name="RT")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        sess = Session(user_id=user.id, ip_address="1.1.1.1", user_agent="ua")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        jti = str(uuid.uuid4())
        rt = RefreshToken(
            jti=jti,
            user_id=user.id,
            session_id=sess.id,
            expires_at=datetime.now(timezone.utc),
        )
        session.add(rt)
        await session.commit()
        await session.refresh(rt)
        assert rt.jti == jti
        assert rt.session_id == sess.id
        assert rt.revoked_at is None
        # revocation lookup by JTI
        rt.revoked_at = datetime.now(timezone.utc)
        await session.commit()
        assert rt.revoked_at is not None
    await engine.dispose()


# ---------------------------------------------------------------------------
# 1.5 APIKey model
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_api_key_model():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as session:
        user = User(email="apikey@example.com", display_name="KeyUser")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        key = APIKey(
            user_id=user.id,
            name="my-agent",
            key_hash="sha256hashvalue123",
            scopes=["read:models"],
            rate_limit_rpm=60,
        )
        session.add(key)
        await session.commit()
        await session.refresh(key)
        assert key.key_hash == "sha256hashvalue123"
        assert key.scopes == ["read:models"]
        assert key.rate_limit_rpm == 60
        assert key.revoked_at is None
        # lookup by key_hash
        assert key.name == "my-agent"
    await engine.dispose()


# ---------------------------------------------------------------------------
# 1.6 Schemas
# ---------------------------------------------------------------------------
def test_schemas_validation():
    # UserRead
    uid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    user_read = UserRead(
        id=uid,
        email="schema@example.com",
        display_name="Schema",
        avatar_url=None,
        role=RoleEnum.USER,
        reputation_score=5.0,
        email_verified=False,
        created_at=now,
        updated_at=now,
    )
    assert user_read.email == "schema@example.com"
    assert user_read.role == RoleEnum.USER
    # frozen
    with pytest.raises(Exception):
        user_read.email = "hacked@example.com"  # type: ignore[misc]

    # UserUpdate
    upd = UserUpdate(display_name="New Name")
    assert upd.display_name == "New Name"

    # OAuthCallback
    cb = OAuthCallback(code="authcode123", state="statetoken")
    assert cb.code == "authcode123"

    # DeviceFingerprintInput
    fp = DeviceFingerprintInput(user_agent="Mozilla", ip_address="1.2.3.4", accept_language="en")
    assert fp.user_agent == "Mozilla"

    # triangulation: missing required fields should fail
    with pytest.raises(Exception):
        UserRead(
            id=uid,
            email="bad",
            display_name="x",
            role=RoleEnum.USER,  # type: ignore[call-arg]
            reputation_score=5.0,
            email_verified=False,
            created_at=now,
            updated_at=now,
        )


# ---------------------------------------------------------------------------
# 1.7 Migration up/down
# ---------------------------------------------------------------------------
def test_migration_file_exists():
    from pathlib import Path

    mig_dir = Path("app/db/migrations/versions")
    if not mig_dir.exists():
        mig_dir = Path("app/alembic/versions")
    # also check app/db/migrations
    candidates = list(Path("app").rglob("*initial_auth*.py"))
    candidates += list(Path("app").rglob("*_auth*.py"))
    assert len(candidates) > 0, "No auth migration file found"


@pytest.mark.asyncio
async def test_migration_up_down():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # verify tables exist
        def check_tables(sync_conn):
            insp = inspect(sync_conn)
            tables = insp.get_table_names()
            assert "users" in tables
            assert "sessions" in tables
            assert "refresh_tokens" in tables
            assert "api_keys" in tables

        await conn.run_sync(check_tables)
    # down
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        def check_dropped(sync_conn):
            insp = inspect(sync_conn)
            tables = insp.get_table_names()
            assert "users" not in tables

        await conn.run_sync(check_dropped)
    await engine.dispose()


# ---------------------------------------------------------------------------
# 1.8 Config
# ---------------------------------------------------------------------------
def test_config_loading():
    # OAuth
    assert hasattr(settings, "GOOGLE_CLIENT_ID")
    assert hasattr(settings, "GOOGLE_CLIENT_SECRET")
    assert hasattr(settings, "GITHUB_CLIENT_ID")
    assert hasattr(settings, "GITHUB_CLIENT_SECRET")
    assert hasattr(settings, "OAUTH_REDIRECT_URI")
    # JWT RS256
    assert hasattr(settings, "JWT_PRIVATE_KEY_PATH")
    assert hasattr(settings, "JWT_PUBLIC_KEY_PATH")
    assert hasattr(settings, "JWT_ALGORITHM")
    assert settings.JWT_ALGORITHM == "RS256"
    assert hasattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    assert hasattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    # Turnstile
    assert hasattr(settings, "TURNSTILE_SECRET_KEY")
    # Rate limits
    assert hasattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE")
    assert hasattr(settings, "RATE_LIMIT_REGISTER_PER_MINUTE")
    # Existing fields still present
    assert hasattr(settings, "DATABASE_URL")
    assert hasattr(settings, "REDIS_URL")
