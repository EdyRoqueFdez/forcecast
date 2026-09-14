"""Phase 5.1 — Orchestrator Repository Tests (TDD RED).

Covers:
- list_approved returns only approved orchestrators
- Pagination works correctly (offset-based)
- Sorting works correctly (name asc/desc)
- Provider fetching works (batch get_providers)
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import (
    Orchestrator,
    OrchestratorProvider,
    OrchestratorTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
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
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as s:
        # Seed base taxonomy version for FK
        v = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(v)
        await s.commit()
        yield s
        await s.rollback()


_seed_counter = 0


async def _seed_orchestrators(session: AsyncSession, count: int = 5, status: str = "approved") -> list[Orchestrator]:
    """Seed N orchestrators with translations and return them."""
    global _seed_counter
    orchs = []
    for i in range(count):
        _seed_counter += 1
        orch = Orchestrator(
            id=str(uuid.uuid4()),
            slug=f"orch-{status[:3]}-{_seed_counter:04d}",
            name=f"Orchestrator {_seed_counter}",
            version=f"1.{_seed_counter}.0",
            maintainer=f"team-{_seed_counter}",
            website=f"https://orch-{_seed_counter}.example.com",
            repo_url=f"https://github.com/orch-{_seed_counter}",
            status=status,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(orch)
        orchs.append(orch)

    await session.flush()

    # Add translations for each
    for orch in orchs:
        for loc, name_suffix in [("en", "EN"), ("es", "ES"), ("fr", "FR")]:
            session.add(OrchestratorTranslation(
                id=str(uuid.uuid4()),
                orchestrator_id=orch.id,
                locale=loc,
                name=f"{orch.name} {name_suffix}",
                description=f"Description {name_suffix} for {orch.slug}",
            ))
    await session.flush()
    return orchs


async def _seed_providers(session: AsyncSession, count: int = 3) -> list[Provider]:
    """Seed providers with translations."""
    provs = []
    for i in range(count):
        p = Provider(
            id=str(uuid.uuid4()),
            slug=f"prov-{i}",
            name=f"Provider {i}",
            status="active",
        )
        session.add(p)
        provs.append(p)
    await session.flush()

    for p in provs:
        session.add(ProviderTranslation(
            id=str(uuid.uuid4()),
            provider_id=p.id,
            locale="en",
            name=f"{p.name} EN",
        ))
    await session.flush()
    return provs


# ---------------------------------------------------------------------------
# 5.1 Repository Tests
# ---------------------------------------------------------------------------
class TestOrchestratorRepository:
    @pytest.mark.asyncio
    async def test_list_approved_returns_only_approved(self, session):
        """list_approved must return only orchestrators with status='approved'."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        # Seed: 3 approved + 2 draft
        await _seed_orchestrators(session, count=3, status="approved")
        await _seed_orchestrators(session, count=2, status="draft")

        repo = OrchestratorRepository(session)
        orchs, total = await repo.list_approved()

        assert total == 3
        assert len(orchs) == 3
        assert all(o.status == "approved" for o in orchs)

    @pytest.mark.asyncio
    async def test_list_approved_pagination_offset(self, session):
        """Pagination with offset/limit returns correct slices."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        await _seed_orchestrators(session, count=10, status="approved")

        repo = OrchestratorRepository(session)

        # First page: limit=3, offset=0
        page1, total = await repo.list_approved(limit=3, offset=0)
        assert total == 10
        assert len(page1) == 3

        # Second page: limit=3, offset=3
        page2, total2 = await repo.list_approved(limit=3, offset=3)
        assert total2 == 10
        assert len(page2) == 3

        # Ensure no overlap
        ids1 = {o.id for o in page1}
        ids2 = {o.id for o in page2}
        assert ids1.isdisjoint(ids2)

        # Last page may have fewer
        last_page, _ = await repo.list_approved(limit=3, offset=9)
        assert len(last_page) == 1

    @pytest.mark.asyncio
    async def test_list_approved_sorting_name_asc(self, session):
        """Sorting by name ascending returns orchestrators in alphabetical order."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        # Seed with names that sort non-trivially
        names = ["Charlie", "Alpha", "Bravo"]
        orchs = []
        for name in names:
            orch = Orchestrator(
                id=str(uuid.uuid4()),
                slug=f"sort-{name.lower()}",
                name=name,
                status="approved",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(orch)
            orchs.append(orch)
        await session.flush()

        repo = OrchestratorRepository(session)
        result, _ = await repo.list_approved(sort="name", order="asc")
        result_names = [o.name for o in result]
        assert result_names == sorted(names)

    @pytest.mark.asyncio
    async def test_list_approved_sorting_name_desc(self, session):
        """Sorting by name descending returns reverse alphabetical order."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        names = ["Charlie", "Alpha", "Bravo"]
        for name in names:
            session.add(Orchestrator(
                id=str(uuid.uuid4()),
                slug=f"sort-desc-{name.lower()}",
                name=name,
                status="approved",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ))
        await session.flush()

        repo = OrchestratorRepository(session)
        result, _ = await repo.list_approved(sort="name", order="desc")
        result_names = [o.name for o in result]
        assert result_names == sorted(names, reverse=True)

    @pytest.mark.asyncio
    async def test_list_approved_translations_loaded(self, session):
        """Orchestrators returned by list_approved have translations eagerly loaded."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        await _seed_orchestrators(session, count=2, status="approved")

        repo = OrchestratorRepository(session)
        orchs, _ = await repo.list_approved()

        for orch in orchs:
            # selectinload should have populated translations
            assert len(orch.translations) == 3  # en, es, fr

    @pytest.mark.asyncio
    async def test_get_by_slug_found(self, session):
        """get_by_slug returns the orchestrator when it exists and is approved."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        await _seed_orchestrators(session, count=1, status="approved")
        orch = (await session.execute(
            __import__("sqlalchemy").select(Orchestrator).limit(1)
        )).scalars().first()

        repo = OrchestratorRepository(session)
        result = await repo.get_by_slug(orch.slug)
        assert result is not None
        assert result.id == orch.id

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(self, session):
        """get_by_slug returns None for non-existent slug."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        repo = OrchestratorRepository(session)
        result = await repo.get_by_slug("non-existent-slug")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_slug_excludes_draft(self, session):
        """get_by_slug returns None for draft orchestrators."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        await _seed_orchestrators(session, count=1, status="draft")
        orch = (await session.execute(
            __import__("sqlalchemy").select(Orchestrator).limit(1)
        )).scalars().first()

        repo = OrchestratorRepository(session)
        result = await repo.get_by_slug(orch.slug)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_providers_batch(self, session):
        """get_providers returns providers grouped by orchestrator_id."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        # Seed orchestrators
        orchs = await _seed_orchestrators(session, count=2, status="approved")
        # Seed providers
        provs = await _seed_providers(session, count=3)

        # Link: orch[0] -> prov[0], prov[1]; orch[1] -> prov[2]
        session.add(OrchestratorProvider(
            orchestrator_id=orchs[0].id, provider_id=provs[0].id,
            created_at=datetime.now(timezone.utc),
        ))
        session.add(OrchestratorProvider(
            orchestrator_id=orchs[0].id, provider_id=provs[1].id,
            created_at=datetime.now(timezone.utc),
        ))
        session.add(OrchestratorProvider(
            orchestrator_id=orchs[1].id, provider_id=provs[2].id,
            created_at=datetime.now(timezone.utc),
        ))
        await session.flush()

        repo = OrchestratorRepository(session)
        providers_map = await repo.get_providers([orchs[0].id, orchs[1].id])

        assert orchs[0].id in providers_map
        assert len(providers_map[orchs[0].id]) == 2
        assert orchs[1].id in providers_map
        assert len(providers_map[orchs[1].id]) == 1

        # Check provider dict shape
        prov_dict = providers_map[orchs[0].id][0]
        assert "id" in prov_dict
        assert "slug" in prov_dict
        assert "name" in prov_dict

    @pytest.mark.asyncio
    async def test_get_providers_empty_ids(self, session):
        """get_providers returns empty dict for empty input."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        repo = OrchestratorRepository(session)
        result = await repo.get_providers([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_providers_uses_en_translation(self, session):
        """get_providers prefers the English translation for provider name."""
        from app.taxonomy.repositories.orchestrator import OrchestratorRepository

        orchs = await _seed_orchestrators(session, count=1, status="approved")
        provs = await _seed_providers(session, count=1)

        # Add ES translation too
        session.add(ProviderTranslation(
            id=str(uuid.uuid4()),
            provider_id=provs[0].id,
            locale="es",
            name="Proveedor ES",
        ))
        session.add(OrchestratorProvider(
            orchestrator_id=orchs[0].id, provider_id=provs[0].id,
            created_at=datetime.now(timezone.utc),
        ))
        await session.flush()

        repo = OrchestratorRepository(session)
        providers_map = await repo.get_providers([orchs[0].id])

        # Should use EN translation name
        assert providers_map[orchs[0].id][0]["name"] == "Provider 0 EN"
