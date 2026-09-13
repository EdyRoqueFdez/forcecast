"""Voting test fixtures."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.session import Base
from app.auth.models.user import User, RoleEnum
from app.taxonomy.models.entities import AIModel, Category, TaxonomyVersion
from app.voting.models.vote_event import VoteEvent
from app.voting.models.user_vote import UserVote
from app.voting.models.audit_log import AuditLog


# Test database URL (SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_voting.db"


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with email verified."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        display_name="Test User",
        role=RoleEnum.USER,
        email_verified=True,
        reputation_score=5.0,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_user_unverified(db_session: AsyncSession) -> User:
    """Create a test user without email verified."""
    user = User(
        id=str(uuid.uuid4()),
        email="unverified@example.com",
        display_name="Unverified User",
        role=RoleEnum.USER,
        email_verified=False,
        reputation_score=5.0,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_user_bot(db_session: AsyncSession) -> User:
    """Create a test user with low reputation (bot signals)."""
    user = User(
        id=str(uuid.uuid4()),
        email="bot@example.com",
        display_name="Bot User",
        role=RoleEnum.USER,
        email_verified=True,
        reputation_score=2.0,  # Below STRICT_THRESHOLD
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_taxonomy_version(db_session: AsyncSession) -> TaxonomyVersion:
    """Create the current taxonomy version."""
    version = TaxonomyVersion(
        id=str(uuid.uuid4()),
        version="1.0.0",
        is_current=True,
        released_at=datetime.now(UTC),
    )
    db_session.add(version)
    await db_session.commit()
    return version


@pytest_asyncio.fixture
async def test_category(db_session: AsyncSession, test_taxonomy_version: TaxonomyVersion) -> Category:
    """Create an active category."""
    category = Category(
        id=str(uuid.uuid4()),
        slug="best-code-model",
        taxonomy_version=test_taxonomy_version.version,
        status="active",
    )
    db_session.add(category)
    await db_session.commit()
    return category


@pytest_asyncio.fixture
async def test_model(db_session: AsyncSession) -> AIModel:
    """Create an approved model."""
    model = AIModel(
        id=str(uuid.uuid4()),
        provider_id=str(uuid.uuid4()),  # Fake provider ID
        slug="gpt-4-test",
        display_name="GPT-4 Test",
        status="approved",
        source="manual",
        source_payload_hash="test-hash",
        modality=["text"],
    )
    db_session.add(model)
    await db_session.commit()
    return model
