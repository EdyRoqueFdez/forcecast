import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import TaxonomyVersion, WebhookDelivery, WebhookRegistration
from app.taxonomy.services.core import DomainError


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
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        v = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(v)
        await s.commit()
        yield s
        await s.rollback()


# ---------------------------------------------------------------------------
# update_registration — invalid events
# ---------------------------------------------------------------------------
class TestWebhookUpdateRegistration:
    @pytest.mark.asyncio
    async def test_update_registration_invalid_events(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        with pytest.raises(DomainError) as exc:
            await repo.update_registration(reg, events=["invalid.event"])
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_update_registration_valid_events(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        updated = await repo.update_registration(reg, events=["model.rejected", "model.approved"])
        assert updated.events == ["model.rejected", "model.approved"]


# ---------------------------------------------------------------------------
# delete_registration
# ---------------------------------------------------------------------------
class TestWebhookDeleteRegistration:
    @pytest.mark.asyncio
    async def test_delete_registration(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        await repo.delete_registration(reg)
        fetched = await repo.get_registration(reg.id)
        assert fetched is None


# ---------------------------------------------------------------------------
# create_delivery — webhook not found
# ---------------------------------------------------------------------------
class TestWebhookCreateDelivery:
    @pytest.mark.asyncio
    async def test_create_delivery_webhook_not_found(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        fake_id = str(uuid.uuid4())
        with pytest.raises(DomainError) as exc:
            await repo.create_delivery(webhook_id=fake_id, event_type="model.approved", payload={}, delivery_id="del-1")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_delivery_integrity_error(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-dup")
            assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# get_delivery — business key lookup + fallback to id
# ---------------------------------------------------------------------------
class TestWebhookGetDelivery:
    @pytest.mark.asyncio
    async def test_get_delivery_by_delivery_id(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        delivery = await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-biz-1")
        found = await repo.get_delivery("del-biz-1")
        assert found is not None
        assert found.id == delivery.id

    @pytest.mark.asyncio
    async def test_get_delivery_fallback_to_pk(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        delivery = await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-fb-1")
        found = await repo.get_delivery(delivery.id)
        assert found is not None
        assert found.delivery_id == "del-fb-1"

    @pytest.mark.asyncio
    async def test_get_delivery_not_found(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        found = await repo.get_delivery("nonexistent")
        assert found is None


# ---------------------------------------------------------------------------
# get_delivery_by_id
# ---------------------------------------------------------------------------
class TestWebhookGetDeliveryById:
    @pytest.mark.asyncio
    async def test_get_delivery_by_id_found(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        delivery = await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-id-1")
        found = await repo.get_delivery_by_id(delivery.id)
        assert found is not None
        assert found.delivery_id == "del-id-1"

    @pytest.mark.asyncio
    async def test_get_delivery_by_id_not_found(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        found = await repo.get_delivery_by_id(str(uuid.uuid4()))
        assert found is None


# ---------------------------------------------------------------------------
# list_deliveries — with filters
# ---------------------------------------------------------------------------
class TestWebhookListDeliveries:
    @pytest.mark.asyncio
    async def test_list_deliveries_all(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-lst-1")
        await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-lst-2")
        all_deliveries = await repo.list_deliveries()
        assert len(all_deliveries) >= 2

    @pytest.mark.asyncio
    async def test_list_deliveries_by_webhook_id(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-lst-w-1")
        filtered = await repo.list_deliveries(webhook_id=reg.id)
        assert all(d.webhook_id == reg.id for d in filtered)

    @pytest.mark.asyncio
    async def test_list_deliveries_by_status(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-lst-s-1")
        filtered = await repo.list_deliveries(status="pending")
        assert all(d.status == "pending" for d in filtered)


# ---------------------------------------------------------------------------
# schedule_retry — fallback, not found, dead_letter
# ---------------------------------------------------------------------------
class TestWebhookScheduleRetry:
    @pytest.mark.asyncio
    async def test_schedule_retry_fallback_lookup_by_delivery_id(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        delivery = await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-rtr-1")
        result = await repo.schedule_retry(delivery.delivery_id, error="timeout")
        assert result.attempt == 2

    @pytest.mark.asyncio
    async def test_schedule_retry_not_found(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        with pytest.raises(DomainError) as exc:
            await repo.schedule_retry(str(uuid.uuid4()), error="timeout")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_schedule_retry_dead_letter_early_return(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        delivery = await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-dl-1")
        # manually set to dead_letter
        delivery.status = "dead_letter"
        await session.commit()
        result = await repo.schedule_retry(delivery.id, error="timeout")
        assert result.status == "dead_letter"

    @pytest.mark.asyncio
    async def test_schedule_retry_dead_letter_at_attempt_6(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        delivery = await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-dl-6")
        # push to attempt 5
        d = delivery
        for _ in range(4):
            d = await repo.schedule_retry(d.id, error="fail")
        # one more should go to dead_letter
        result = await repo.schedule_retry(d.id, error="final")
        assert result.status == "dead_letter"
        assert result.next_retry_at is None


# ---------------------------------------------------------------------------
# mark_delivered
# ---------------------------------------------------------------------------
class TestWebhookMarkDelivered:
    @pytest.mark.asyncio
    async def test_mark_delivered_success(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        delivery = await repo.create_delivery(webhook_id=reg.id, event_type="model.approved", payload={}, delivery_id="del-md-1")
        result = await repo.mark_delivered(delivery.id, response_status=200, response_body="OK")
        assert result.status == "delivered"
        assert result.response_status == 200
        assert result.response_body == "OK"
        assert result.delivered_at is not None
        assert result.next_retry_at is None

    @pytest.mark.asyncio
    async def test_mark_delivered_not_found(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        with pytest.raises(DomainError) as exc:
            await repo.mark_delivered(str(uuid.uuid4()), response_status=200)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# should_deliver — inactive / not found
# ---------------------------------------------------------------------------
class TestWebhookShouldDeliver:
    @pytest.mark.asyncio
    async def test_should_deliver_inactive(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"], is_active=False)
        result = await repo.should_deliver(reg.id, "model.approved")
        assert result is False

    @pytest.mark.asyncio
    async def test_should_deliver_not_found(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        result = await repo.should_deliver(str(uuid.uuid4()), "model.approved")
        assert result is False

    @pytest.mark.asyncio
    async def test_should_deliver_events_not_list(self, session):
        from app.taxonomy.repositories.webhook import WebhookRepository
        repo = WebhookRepository(session)
        reg = await repo.create_registration(url="https://hook.com", secret="s", events=["model.approved"])
        reg.events = "not-a-list"
        await session.commit()
        result = await repo.should_deliver(reg.id, "model.approved")
        assert result is False
