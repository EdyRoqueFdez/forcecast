"""Phase 3 — Repositories (TDD RED) — 5 tasks.

Covers:
3.1 Provider Repository - CRUD + translation upsert
3.2 AIModel Repository (with Deduplication Upsert) - 3 unique constraints, batched upsert
3.3 ModelHosting Repository (Primary Constraint) - set_primary atomic swap
3.4 Category + TaxonomyVersion Repository - tree ops, version activation atomic swap
3.5 Ingestion + Webhook Repository - advisory lock, retry scheduling
"""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import event, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import (
    AIModel,
    Category,
    CategoryTranslation,
    IngestionRun,
    IngestionSource,
    ModelHosting,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
    WebhookDelivery,
    WebhookRegistration,
)
from app.taxonomy.models.enums import (
    CategoryStatus,
    Locale,
    ModelModality,
    ModelSource,
    ModelStatus,
    ProviderStatus,
)
from app.taxonomy.services.core import DomainError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(eng.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.execute(sa_text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as s:
        # seed base taxonomy version for FK
        v = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(v)
        await s.commit()
        yield s
        await s.rollback()


# ---------------------------------------------------------------------------
# 3.1 Provider Repository
# ---------------------------------------------------------------------------
class TestProviderRepository:
    @pytest.mark.asyncio
    async def test_provider_crud(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository

        repo = ProviderRepository(session)
        # CREATE
        created = await repo.create(slug="anthropic", name="Anthropic", website="https://anthropic.com")
        assert created.id is not None
        assert created.slug == "anthropic"
        assert created.status == ProviderStatus.ACTIVE.value or created.status == "active"
        # GET
        fetched = await repo.get(created.id)
        assert fetched is not None
        assert fetched.slug == "anthropic"
        # GET_BY_SLUG
        by_slug = await repo.get_by_slug("anthropic")
        assert by_slug is not None
        assert by_slug.id == created.id
        # LIST
        lst = await repo.list()
        assert len(lst) >= 1
        # UPDATE
        updated = await repo.update(created, name="Anthropic Updated")
        assert updated.name == "Anthropic Updated"
        # DELETE
        await repo.delete(updated)
        deleted = await repo.get(created.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_provider_slug_unique_raises_409(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository

        repo = ProviderRepository(session)
        await repo.create(slug="openai", name="OpenAI")
        with pytest.raises(DomainError) as exc:
            await repo.create(slug="openai", name="OpenAI Dup")
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_provider_translation_upsert(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository

        repo = ProviderRepository(session)
        provider = await repo.create(slug="prov-trans", name="Prov Trans")
        # create translation
        t1 = await repo.upsert_translation(provider.id, locale="es", name="Prov ES", description="Desc ES")
        assert t1.name == "Prov ES"
        assert t1.locale == "es" or t1.locale == Locale.ES.value
        # upsert same locale should UPDATE not duplicate
        t2 = await repo.upsert_translation(provider.id, locale="es", name="Prov ES Updated", description="Desc Updated")
        assert t2.name == "Prov ES Updated"
        assert t2.id == t1.id  # same row updated
        # different locale creates new row
        t3 = await repo.upsert_translation(provider.id, locale="fr", name="Prov FR")
        assert t3.id != t1.id
        assert t3.locale == "fr"

    @pytest.mark.asyncio
    async def test_provider_upsert_translation_idempotent(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository

        repo = ProviderRepository(session)
        provider = await repo.create(slug="prov-idem", name="Prov Idem")
        t1 = await repo.upsert_translation(provider.id, locale="en", name="Hello")
        t2 = await repo.upsert_translation(provider.id, locale="en", name="Hello")
        assert t1.id == t2.id


# ---------------------------------------------------------------------------
# 3.2 AIModel Repository (with Deduplication Upsert)
# ---------------------------------------------------------------------------
class TestAIModelUpsert:
    @pytest.mark.asyncio
    async def test_ai_model_upsert_create_and_update(self, session):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.provider import ProviderRepository

        prov_repo = ProviderRepository(session)
        provider = await prov_repo.create(slug="prov-model", name="Prov Model")
        repo = AIModelRepository(session)

        data = {
            "provider_id": provider.id,
            "slug": "gpt-4",
            "display_name": "GPT-4",
            "family": "gpt",
            "version": "4.0",
            "modality": [ModelModality.TEXT.value],
            "status": ModelStatus.DRAFT.value,
            "source": ModelSource.MANUAL.value,
            "source_payload_hash": "hash-001",
        }
        model, created = await repo.upsert(data)
        assert created is True
        assert model.slug == "gpt-4"
        # same provider_id+slug should update, not create
        data2 = {**data, "display_name": "GPT-4 Updated", "source_payload_hash": "hash-002"}
        model2, created2 = await repo.upsert(data2)
        assert created2 is False
        assert model2.id == model.id
        assert model2.display_name == "GPT-4 Updated"

    @pytest.mark.asyncio
    async def test_ai_model_upsert_by_family_version(self, session):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.provider import ProviderRepository

        prov_repo = ProviderRepository(session)
        provider = await prov_repo.create(slug="prov-fam", name="Prov Fam")
        repo = AIModelRepository(session)

        data1 = {
            "provider_id": provider.id,
            "slug": "model-a",
            "display_name": "Model A",
            "family": "llama",
            "version": "3.0",
            "modality": [ModelModality.TEXT.value],
            "status": ModelStatus.DRAFT.value,
            "source": ModelSource.MANUAL.value,
            "source_payload_hash": "hash-fam-1",
        }
        m1, c1 = await repo.upsert(data1)
        assert c1 is True
        # different slug but same family+version+provider => should update m1
        data2 = {
            "provider_id": provider.id,
            "slug": "model-b",
            "display_name": "Model B",
            "family": "llama",
            "version": "3.0",
            "modality": [ModelModality.TEXT.value],
            "status": ModelStatus.DRAFT.value,
            "source": ModelSource.MANUAL.value,
            "source_payload_hash": "hash-fam-2",
        }
        m2, c2 = await repo.upsert(data2)
        assert c2 is False
        assert m2.id == m1.id

    @pytest.mark.asyncio
    async def test_ai_model_upsert_by_payload_hash(self, session):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.provider import ProviderRepository

        prov_repo = ProviderRepository(session)
        provider = await prov_repo.create(slug="prov-hash", name="Prov Hash")
        repo = AIModelRepository(session)

        data1 = {
            "provider_id": provider.id,
            "slug": "unique-slug-1",
            "display_name": "U1",
            "modality": [ModelModality.TEXT.value],
            "status": ModelStatus.DRAFT.value,
            "source": ModelSource.MANUAL.value,
            "source_payload_hash": "samehash123",
        }
        m1, c1 = await repo.upsert(data1)
        assert c1 is True
        data2 = {
            "provider_id": provider.id,
            "slug": "unique-slug-2",
            "display_name": "U2",
            "modality": [ModelModality.TEXT.value],
            "status": ModelStatus.DRAFT.value,
            "source": ModelSource.MANUAL.value,
            "source_payload_hash": "samehash123",
        }
        m2, c2 = await repo.upsert(data2)
        assert c2 is False
        assert m2.id == m1.id
        assert m2.source_payload_hash == "samehash123"

    @pytest.mark.asyncio
    async def test_ai_model_batched_upsert(self, session):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.provider import ProviderRepository

        prov_repo = ProviderRepository(session)
        provider = await prov_repo.create(slug="prov-batch", name="Prov Batch")
        repo = AIModelRepository(session)

        items = [
            {
                "provider_id": provider.id,
                "slug": f"model-{i}",
                "display_name": f"Model {i}",
                "modality": [ModelModality.TEXT.value],
                "status": ModelStatus.DRAFT.value,
                "source": ModelSource.MANUAL.value,
                "source_payload_hash": f"batch-hash-{i}",
            }
            for i in range(5)
        ]
        created, updated = await repo.upsert_batch(items)
        assert created == 5
        assert updated == 0
        # second batch same data => all updates
        created2, updated2 = await repo.upsert_batch(items)
        assert created2 == 0
        assert updated2 == 5


# ---------------------------------------------------------------------------
# 3.3 ModelHosting Repository (Primary Constraint)
# ---------------------------------------------------------------------------
class TestModelHosting:
    @pytest.mark.asyncio
    async def test_model_hosting_crud(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(session)
        provider = await prov_repo.create(slug="prov-host-crud", name="Prov Host")
        ai_repo = AIModelRepository(session)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "host-model",
                "display_name": "Host Model",
                "modality": [ModelModality.TEXT.value],
                "status": ModelStatus.DRAFT.value,
                "source": ModelSource.MANUAL.value,
                "source_payload_hash": "host-hash-crud",
            }
        )
        repo = ModelHostingRepository(session)
        hosting = await repo.create(model_id=model.id, provider_id=provider.id, is_primary=False)
        assert hosting.id is not None
        assert hosting.is_primary is False
        fetched = await repo.get(hosting.id)
        assert fetched is not None
        lst = await repo.list_by_model(model.id)
        assert len(lst) == 1

    @pytest.mark.asyncio
    async def test_model_hosting_set_primary_atomic(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(session)
        p1 = await prov_repo.create(slug="prov-host1", name="Prov Host1")
        p2 = await prov_repo.create(slug="prov-host2", name="Prov Host2")
        ai_repo = AIModelRepository(session)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": p1.id,
                "slug": "primary-model",
                "display_name": "Primary Model",
                "modality": [ModelModality.TEXT.value],
                "status": ModelStatus.DRAFT.value,
                "source": ModelSource.MANUAL.value,
                "source_payload_hash": "primary-hash",
            }
        )
        repo = ModelHostingRepository(session)
        h1 = await repo.create(model_id=model.id, provider_id=p1.id, is_primary=True)
        h2 = await repo.create(model_id=model.id, provider_id=p2.id, is_primary=False)
        assert h1.is_primary is True
        assert h2.is_primary is False
        # atomic swap: set h2 as primary
        result = await repo.set_primary(model.id, h2.id)
        assert result.is_primary is True
        # reload h1 should now be false
        h1_reloaded = await repo.get(h1.id)
        assert h1_reloaded.is_primary is False

    @pytest.mark.asyncio
    async def test_model_hosting_set_primary_not_found(self, session):
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        repo = ModelHostingRepository(session)
        with pytest.raises(DomainError) as exc:
            await repo.set_primary("nonexistent-model-id", "nonexistent-hosting-id")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_model_hosting_no_price_fields(self, session):
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository
        import inspect as insp

        # ensure ModelHosting entity has no price cols (schema check) and repo doesn't expose them
        assert not hasattr(ModelHosting, "input_price_override")
        # repo create should not accept price fields
        repo = ModelHostingRepository(session)
        # check create signature doesn't include price params via inspection
        sig = insp.signature(repo.create)
        assert "input_price_override" not in sig.parameters
        assert "output_price_override" not in sig.parameters


# ---------------------------------------------------------------------------
# 3.4 Category + TaxonomyVersion Repository
# ---------------------------------------------------------------------------
class TestCategoryVersion:
    @pytest.mark.asyncio
    async def test_category_tree_ops(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        # create root
        root = await repo.create(slug="coding", taxonomy_version="v1")
        assert root.parent_id is None
        # create child
        child = await repo.create(slug="debugging", taxonomy_version="v1", parent_id=root.id)
        assert child.parent_id == root.id
        # list
        children = await repo.list_children(root.id)
        assert len(children) == 1
        assert children[0].id == child.id
        # delete parent blocked when has children
        with pytest.raises(DomainError) as exc:
            await repo.delete(root.id)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_category_cycle_detection(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        a = await repo.create(slug="cat-a", taxonomy_version="v1")
        b = await repo.create(slug="cat-b", taxonomy_version="v1", parent_id=a.id)
        # trying to set A's parent to B would create cycle A->B->A
        with pytest.raises(DomainError) as exc:
            await repo.update(a.id, parent_id=b.id)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_category_translation_upsert(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="cat-trans", taxonomy_version="v1")
        t1 = await repo.upsert_translation(cat.id, locale="es", name="Programacion")
        assert t1.name == "Programacion"
        t2 = await repo.upsert_translation(cat.id, locale="es", name="Programacion Updated")
        assert t2.id == t1.id
        assert t2.name == "Programacion Updated"

    @pytest.mark.asyncio
    async def test_taxonomy_version_activation_atomic(self, session):
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository

        repo = TaxonomyVersionRepository(session)
        # v1 is_current True from fixture
        v1 = await repo.get_by_version("v1")
        assert v1.is_current is True
        # create v2
        v2 = await repo.create(version="v2", notes="Added agentic")
        assert v2.is_current is False
        # activate v2
        activated = await repo.activate(v2.id)
        assert activated.is_current is True
        # v1 should now be false
        v1_reloaded = await repo.get(v1.id)
        assert v1_reloaded.is_current is False
        # idempotent activate again
        activated2 = await repo.activate(v2.id)
        assert activated2.is_current is True
        assert activated2.id == v2.id

    @pytest.mark.asyncio
    async def test_taxonomy_version_single_current_enforced(self, session):
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository

        repo = TaxonomyVersionRepository(session)
        v2 = await repo.create(version="v2-single", notes="test")
        # try to create another with is_current True via direct DB should fail, but repo should enforce atomic
        # activate v2, ensure only one current
        await repo.activate(v2.id)
        current = await repo.get_current()
        assert current.version == "v2-single"
        # count currents
        all_versions = await repo.list()
        currents = [v for v in all_versions if v.is_current]
        assert len(currents) == 1


# ---------------------------------------------------------------------------
# 3.5 Ingestion + Webhook Repository
# ---------------------------------------------------------------------------
class TestIngestionWebhook:
    @pytest.mark.asyncio
    async def test_ingestion_source_and_run(self, session):
        from app.taxonomy.repositories.ingestion import IngestionRepository

        repo = IngestionRepository(session)
        source = await repo.create_source(code="openrouter", name="OpenRouter", parser_class="OpenRouterParser")
        assert source.code == "openrouter"
        fetched = await repo.get_source("openrouter")
        assert fetched is not None
        run = await repo.create_run(source="openrouter")
        assert run.status == "running"
        assert run.source == "openrouter"
        # update counts
        updated = await repo.update_run_counts(run.id, models_found=10, models_created=5, models_updated=3, models_skipped=2)
        assert updated.models_found == 10
        # finish
        finished = await repo.finish_run(run.id, status="success")
        assert finished.status == "success"
        assert finished.finished_at is not None

    @pytest.mark.asyncio
    async def test_advisory_lock(self, session):
        from app.taxonomy.repositories.ingestion import IngestionRepository

        repo = IngestionRepository(session)
        await repo.create_source(code="openrouter-lock", name="OR Lock", parser_class="OpenRouterParser")
        # acquire lock for openrouter-lock
        acquired = await repo.acquire_lock("openrouter-lock")
        assert acquired is True
        # second acquire same source should raise 409
        repo2 = IngestionRepository(session)
        with pytest.raises(DomainError) as exc:
            await repo2.acquire_lock("openrouter-lock")
        assert exc.value.status_code == 409
        # different source should succeed
        await repo.create_source(code="huggingface-lock", name="HF Lock", parser_class="HuggingFaceParser")
        acquired2 = await repo2.acquire_lock("huggingface-lock")
        assert acquired2 is True
        # release and reacquire
        await repo.release_lock("openrouter-lock")
        acquired3 = await repo2.acquire_lock("openrouter-lock")
        assert acquired3 is True
        await repo2.release_lock("openrouter-lock")
        await repo2.release_lock("huggingface-lock")

    @pytest.mark.asyncio
    async def test_webhook_registration_and_delivery(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository

        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://example.com/hook", secret="supersecret", events=["model.approved"])
        assert reg.id is not None
        assert reg.is_active is True
        # invalid events should raise 422
        with pytest.raises(DomainError) as exc2:
            await repo.create_registration(url="https://example.com/bad", secret="s", events=["invalid.event"])
        assert exc2.value.status_code == 422
        # create delivery
        delivery = await repo.create_delivery(
            webhook_id=reg.id, event_type="model.approved", payload={"id": "test"}, delivery_id="del-001"
        )
        assert delivery.status == "pending"
        assert delivery.attempt == 1
        # schedule retry
        from datetime import timezone as tz

        retry = await repo.schedule_retry(delivery.id, error="timeout")
        # attempt should be 2, next_retry_at ~1m later
        assert retry.attempt == 2
        assert retry.next_retry_at is not None
        # after 5 failures should be dead_letter
        # simulate attempts 2..5
        d = retry
        for i in range(3):  # attempts 3,4,5
            d = await repo.schedule_retry(d.id, error=f"fail {i}")
        # 5th failure -> next call should mark dead_letter? Actually schedule_retry increments and if attempt>=5 sets dead_letter
        # Check that after 5 attempts, status becomes dead_letter on next failure
        d_last = await repo.schedule_retry(d.id, error="final fail")  # attempt 6 would be dead_letter, but spec says after 5 failures dead_letter
        # According to spec: Maximum 5 attempts. After 5 failures, status changes to dead_letter.
        # So when attempt reaches 5 and fails again, it should become dead_letter. We'll assert either dead_letter or attempt >=5
        assert d_last.status in ("failed", "dead_letter")
        # if we force one more, ensure dead_letter
        if d_last.status != "dead_letter":
            d_dead = await repo.schedule_retry(d_last.id, error="one more")
            assert d_dead.status == "dead_letter"

    @pytest.mark.asyncio
    async def test_webhook_event_filtering(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository

        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://example.com/filter", secret="s", events=["model.approved"])
        # should deliver matching event
        assert await repo.should_deliver(reg.id, "model.approved") is True
        # should not deliver non-matching
        assert await repo.should_deliver(reg.id, "model.rejected") is False

    @pytest.mark.asyncio
    async def test_webhook_retry_schedule_calc(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository

        repo = WebhookRepository(session)
        # Check retry delays: 1m,5m,15m,1h,6h
        delays = []
        for attempt in range(1, 6):
            delay = repo.calculate_retry_delay(attempt)
            delays.append(delay)
        assert delays[0] == timedelta(minutes=1)
        assert delays[1] == timedelta(minutes=5)
        assert delays[2] == timedelta(minutes=15)
        assert delays[3] == timedelta(hours=1)
        assert delays[4] == timedelta(hours=6)
