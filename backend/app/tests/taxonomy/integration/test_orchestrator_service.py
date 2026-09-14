"""Phase 5.2 — Orchestrator Service Tests (TDD RED).

Covers:
- list_orchestrators with locale (i18n fallback chain)
- Cache behavior (hit/miss, invalidation)
- Cursor pagination (has_more, next_cursor)
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
    Category,
    Orchestrator,
    OrchestratorCategory,
    OrchestratorProvider,
    OrchestratorTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
)
from app.taxonomy.services.public import PublicService, clear_cache


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
        v = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(v)
        await s.commit()
        yield s
        await s.rollback()


@pytest_asyncio.fixture(autouse=True)
def _clear_cache():
    """Clear in-memory cache before each test."""
    clear_cache()
    yield
    clear_cache()


async def _seed_orchestrators(session: AsyncSession, count: int = 5) -> list[Orchestrator]:
    """Seed N approved orchestrators with multi-locale translations."""
    orchs = []
    for i in range(count):
        orch = Orchestrator(
            id=str(uuid.uuid4()),
            slug=f"orch-{i:03d}",
            name=f"Orchestrator {i}",
            version=f"1.{i}.0",
            maintainer=f"team-{i}",
            website=f"https://orch-{i}.example.com",
            repo_url=f"https://github.com/orch-{i}",
            status="approved",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(orch)
        orchs.append(orch)
    await session.flush()

    for orch in orchs:
        for loc, name_suf, desc_suf in [
            ("en", "EN", "English desc"),
            ("es", "ES", "Descripción ES"),
            ("fr", "FR", "Description FR"),
        ]:
            session.add(OrchestratorTranslation(
                id=str(uuid.uuid4()),
                orchestrator_id=orch.id,
                locale=loc,
                name=f"{orch.name} {name_suf}",
                description=f"{desc_suf} for {orch.slug}",
            ))
    await session.flush()
    return orchs


async def _seed_providers_and_link(session: AsyncSession, orchs: list[Orchestrator], prov_count: int = 2):
    """Seed providers and link them to the first orchestrator."""
    provs = []
    for i in range(prov_count):
        p = Provider(id=str(uuid.uuid4()), slug=f"prov-{i}", name=f"Provider {i}", status="active")
        session.add(p)
        provs.append(p)
    await session.flush()

    for p in provs:
        session.add(ProviderTranslation(
            id=str(uuid.uuid4()), provider_id=p.id, locale="en", name=f"{p.name} EN",
        ))

    # Link first provider to first orchestrator
    if orchs and provs:
        session.add(OrchestratorProvider(
            orchestrator_id=orchs[0].id, provider_id=provs[0].id,
            created_at=datetime.now(timezone.utc),
        ))
    await session.flush()
    return provs


# ---------------------------------------------------------------------------
# 5.2 Service Tests — Locale / i18n
# ---------------------------------------------------------------------------
class TestOrchestratorLocale:
    @pytest.mark.asyncio
    async def test_list_orchestrators_locale_en(self, session):
        """English locale returns English names."""
        orchs = await _seed_orchestrators(session, count=2)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        items, total = await svc.list_orchestrators(locale="en", use_cache=False)

        assert total == 2
        assert len(items) == 2
        for item in items:
            assert item["locale_used"] == "en"
            assert "EN" in item["name"]

    @pytest.mark.asyncio
    async def test_list_orchestrators_locale_es(self, session):
        """Spanish locale returns Spanish names."""
        orchs = await _seed_orchestrators(session, count=2)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        items, total = await svc.list_orchestrators(locale="es", use_cache=False)

        assert total == 2
        for item in items:
            assert item["locale_used"] == "es"
            assert "ES" in item["name"]

    @pytest.mark.asyncio
    async def test_list_orchestrators_locale_fallback_to_en(self, session):
        """Unsupported locale falls back to English."""
        orchs = await _seed_orchestrators(session, count=1)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        # Request 'pt' which has no translations — should fallback to 'en'
        items, total = await svc.list_orchestrators(locale="pt", use_cache=False)

        assert total == 1
        assert items[0]["locale_used"] == "en"
        assert "EN" in items[0]["name"]

    @pytest.mark.asyncio
    async def test_list_orchestrators_no_translations_uses_entity_name(self, session):
        """Orchestrator with no translations falls back to entity.name."""
        orch = Orchestrator(
            id=str(uuid.uuid4()), slug="bare-orch", name="Bare Orchestrator",
            status="approved",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        session.add(orch)
        await session.flush()

        svc = PublicService(session)
        items, total = await svc.list_orchestrators(locale="en", use_cache=False)

        assert total == 1
        assert items[0]["name"] == "Bare Orchestrator"
        assert items[0]["locale_used"] == "en"

    @pytest.mark.asyncio
    async def test_list_orchestrators_providers_in_response(self, session):
        """Each orchestrator item includes its linked providers."""
        orchs = await _seed_orchestrators(session, count=1)
        await _seed_providers_and_link(session, orchs, prov_count=2)

        svc = PublicService(session)
        items, _ = await svc.list_orchestrators(locale="en", use_cache=False)

        assert len(items) == 1
        providers = items[0]["providers"]
        assert len(providers) >= 1
        assert all("slug" in p and "name" in p for p in providers)


# ---------------------------------------------------------------------------
# 5.2 Service Tests — Cache
# ---------------------------------------------------------------------------
class TestOrchestratorCache:
    @pytest.mark.asyncio
    async def test_cache_hit_returns_same_result(self, session):
        """Second call with same params hits cache and returns identical result."""
        orchs = await _seed_orchestrators(session, count=3)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        items1, total1 = await svc.list_orchestrators(locale="en", use_cache=True)
        items2, total2 = await svc.list_orchestrators(locale="en", use_cache=True)

        assert total1 == total2
        assert [i["id"] for i in items1] == [i["id"] for i in items2]

    @pytest.mark.asyncio
    async def test_cache_disabled_always_queries(self, session):
        """use_cache=False always queries the DB."""
        orchs = await _seed_orchestrators(session, count=2)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        items1, _ = await svc.list_orchestrators(locale="en", use_cache=False)
        items2, _ = await svc.list_orchestrators(locale="en", use_cache=False)

        assert len(items1) == len(items2) == 2

    @pytest.mark.asyncio
    async def test_different_locale_different_cache_key(self, session):
        """Different locales produce different cache keys and different results."""
        orchs = await _seed_orchestrators(session, count=2)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        items_en, _ = await svc.list_orchestrators(locale="en", use_cache=True)
        items_es, _ = await svc.list_orchestrators(locale="es", use_cache=True)

        assert items_en[0]["name"] != items_es[0]["name"]
        assert items_en[0]["locale_used"] == "en"
        assert items_es[0]["locale_used"] == "es"


# ---------------------------------------------------------------------------
# 5.2 Service Tests — Cursor Pagination
# ---------------------------------------------------------------------------
class TestOrchestratorCursorPagination:
    @pytest.mark.asyncio
    async def test_cursor_pagination_has_more(self, session):
        """When more results exist, has_more=True and next_cursor is set."""
        orchs = await _seed_orchestrators(session, count=5)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        items, total = await svc.list_orchestrators(locale="en", limit=2, use_cache=False)

        assert total == 5
        assert len(items) == 2
        # With 5 total and limit 2, there should be more
        # The API layer builds has_more; service returns raw items + total
        assert total > len(items)

    @pytest.mark.asyncio
    async def test_cursor_pagination_second_page(self, session):
        """Using cursor from first page returns the next set of results."""
        orchs = await _seed_orchestrators(session, count=5)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        # Sort by id to match cursor pagination (cursor encodes id)
        items1, _ = await svc.list_orchestrators(locale="en", limit=2, sort="id", use_cache=False)

        # Build cursor from last item
        from app.taxonomy.services.public import encode_cursor
        cursor = encode_cursor(items1[-1])

        items2, _ = await svc.list_orchestrators(locale="en", limit=2, cursor=cursor, sort="id", use_cache=False)

        # No overlap between pages
        ids1 = {i["id"] for i in items1}
        ids2 = {i["id"] for i in items2}
        assert ids1.isdisjoint(ids2)

    @pytest.mark.asyncio
    async def test_cursor_pagination_exhausts_results(self, session):
        """Paginating through all results yields every orchestrator exactly once."""
        orchs = await _seed_orchestrators(session, count=7)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        all_ids = []
        cursor = None
        limit = 3

        while True:
            items, total = await svc.list_orchestrators(locale="en", limit=limit, cursor=cursor, sort="id", use_cache=False)
            if not items:
                break
            all_ids.extend(i["id"] for i in items)
            if len(items) < limit:
                break
            from app.taxonomy.services.public import encode_cursor
            cursor = encode_cursor(items[-1])

        assert len(all_ids) == 7
        assert len(set(all_ids)) == 7  # no duplicates

    @pytest.mark.asyncio
    async def test_cursor_pagination_empty_result(self, session):
        """Pagination beyond total returns empty list."""
        orchs = await _seed_orchestrators(session, count=2)
        await _seed_providers_and_link(session, orchs)

        svc = PublicService(session)
        items1, _ = await svc.list_orchestrators(locale="en", limit=10, sort="id", use_cache=False)
        assert len(items1) == 2

        from app.taxonomy.services.public import encode_cursor
        # Build a cursor from a dummy item with a very high id to ensure no results
        cursor = encode_cursor({"id": "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz", "slug": "past-the-end"})
        items2, _ = await svc.list_orchestrators(locale="en", limit=10, cursor=cursor, sort="id", use_cache=False)
        assert len(items2) == 0
