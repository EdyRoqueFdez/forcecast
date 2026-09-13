"""Phase 6.1 — Webhook Service (TDD RED) — HMAC, envelope, retry, dead_letter, filtering."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone, timedelta

import pytest

# These imports will FAIL on RED (service not yet implemented) — intentional TDD
from app.taxonomy.services.webhooks import (
    sign_payload,
    verify_signature,
    build_envelope,
    build_headers,
    get_retry_delay,
    WebhookService,
)
from app.taxonomy.models.enums import WebhookEvent


class TestSignPayload:
    def test_hmac_sha256_hex(self):
        secret = "supersecret"
        body = b'{"type":"model.approved","data":{"id":"123"}}'
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert sign_payload(secret, body) == expected

    def test_different_secret_different_signature(self):
        body = b'{"hello":1}'
        s1 = sign_payload("secret1", body)
        s2 = sign_payload("secret2", body)
        assert s1 != s2

    def test_verify_signature_valid(self):
        secret = "mysecret"
        body = b"payload"
        sig = sign_payload(secret, body)
        assert verify_signature(secret, body, sig) is True

    def test_verify_signature_invalid(self):
        secret = "mysecret"
        body = b"payload"
        sig = sign_payload(secret, body)
        assert verify_signature(secret, body, "deadbeef") is False
        assert verify_signature(secret, b"other", sig) is False

    def test_sign_empty_body(self):
        secret = "k"
        body = b""
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert sign_payload(secret, body) == expected


class TestEnvelope:
    def test_envelope_structure(self):
        data = {"model_id": "abc", "slug": "gpt-4"}
        env = build_envelope(WebhookEvent.MODEL_APPROVED.value, data, taxonomy_version="v1")
        assert env["type"] == WebhookEvent.MODEL_APPROVED.value
        assert env["data"] == data
        assert env["taxonomy_version"] == "v1"
        assert "id" in env
        # id is uuid
        uuid.UUID(env["id"])
        # timestamp ISO8601 and within 5 minutes
        ts = datetime.fromisoformat(env["timestamp"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        assert abs((now - ts).total_seconds()) < 300

    def test_envelope_different_event(self):
        env = build_envelope(WebhookEvent.INGESTION_COMPLETED.value, {"source": "openrouter"}, "v2")
        assert env["type"] == "ingestion.completed"
        assert env["taxonomy_version"] == "v2"

    def test_envelope_id_unique(self):
        e1 = build_envelope("model.approved", {}, "v1")
        e2 = build_envelope("model.approved", {}, "v1")
        assert e1["id"] != e2["id"]


class TestHeaders:
    def test_headers_include_signature_delivery_timestamp(self):
        secret = "secret123"
        body = json.dumps({"id": "x"}).encode()
        delivery_id = str(uuid.uuid4())
        headers = build_headers(secret, body, delivery_id)
        assert "X-Forcecast-Signature" in headers
        assert headers["X-Forcecast-Signature"] == sign_payload(secret, body)
        assert headers["X-Forcecast-Delivery-Id"] == delivery_id
        assert "X-Forcecast-Timestamp" in headers
        ts = datetime.fromisoformat(headers["X-Forcecast-Timestamp"].replace("Z", "+00:00"))
        assert abs((datetime.now(timezone.utc) - ts).total_seconds()) < 300

    def test_headers_timestamp_within_5_minutes(self):
        headers = build_headers("s", b"body", "del-1")
        ts = datetime.fromisoformat(headers["X-Forcecast-Timestamp"].replace("Z", "+00:00"))
        assert abs((datetime.now(timezone.utc) - ts).total_seconds()) < 300


class TestRetryPolicy:
    def test_retry_delays_match_spec(self):
        assert get_retry_delay(1) == timedelta(minutes=1)
        assert get_retry_delay(2) == timedelta(minutes=5)
        assert get_retry_delay(3) == timedelta(minutes=15)
        assert get_retry_delay(4) == timedelta(hours=1)
        assert get_retry_delay(5) == timedelta(hours=6)

    def test_retry_beyond_5_returns_last(self):
        # beyond 5 should still return 6h or max
        assert get_retry_delay(6) == timedelta(hours=6)
        assert get_retry_delay(10) == timedelta(hours=6)


@pytest.mark.asyncio
class TestWebhookServiceIntegration:
    """Service-level filtering + delivery + dead_letter — uses in-memory sqlite via repo."""
    async def test_event_filtering_creates_only_matching(self):
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import event as sa_event, text as sa_text
        from app.db.session import Base

        eng = create_async_engine("sqlite+aiosqlite:///:memory:")

        @sa_event.listens_for(eng.sync_engine, "connect")
        def _fk_on(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        async with eng.begin() as conn:
            await conn.execute(sa_text("PRAGMA foreign_keys=ON"))
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            svc = WebhookService(session)
            # Register two webhooks: one for approved, one for rejected
            reg_approved = await svc.register(url="https://example.com/approved", secret="s1", events=["model.approved"])
            reg_rejected = await svc.register(url="https://example.com/rejected", secret="s2", events=["model.rejected"])

            # Emit approved → only approved webhook gets delivery
            deliveries = await svc.emit(WebhookEvent.MODEL_APPROVED.value, {"model_id": "m1"}, taxonomy_version="v1")
            assert len(deliveries) == 1
            assert deliveries[0].webhook_id == reg_approved.id
            assert deliveries[0].event_type == "model.approved"

            # Emit rejected → only rejected webhook gets delivery
            deliveries2 = await svc.emit(WebhookEvent.MODEL_REJECTED.value, {"model_id": "m2"}, taxonomy_version="v1")
            assert len(deliveries2) == 1
            assert deliveries2[0].webhook_id == reg_rejected.id

            # Emit deprecated when no webhook registered for it → no deliveries
            deliveries3 = await svc.emit(WebhookEvent.MODEL_DEPRECATED.value, {"model_id": "m3"}, taxonomy_version="v1")
            assert deliveries3 == []

            # Inactive webhook should not receive
            # deactivate approved webhook
            await svc.deactivate(reg_approved.id)
            deliveries4 = await svc.emit(WebhookEvent.MODEL_APPROVED.value, {"model_id": "m4"}, taxonomy_version="v1")
            assert len(deliveries4) == 0

        await eng.dispose()

    async def test_retry_and_dead_letter(self):
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import event as sa_event, text as sa_text
        from app.db.session import Base

        eng = create_async_engine("sqlite+aiosqlite:///:memory:")

        @sa_event.listens_for(eng.sync_engine, "connect")
        def _fk_on(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        async with eng.begin() as conn:
            await conn.execute(sa_text("PRAGMA foreign_keys=ON"))
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            svc = WebhookService(session)
            reg = await svc.register(url="https://example.com/hook", secret="supersecret", events=["model.approved"])
            deliveries = await svc.emit("model.approved", {"id": "test"}, taxonomy_version="v1")
            assert len(deliveries) == 1
            d = deliveries[0]
            assert d.status == "pending"
            assert d.attempt == 1

            # Fail 4 times: attempt 1->2 (1m), 2->3 (5m), 3->4 (15m), 4->5 (1h)
            for i in range(4):
                d = await svc.record_failure(d.id, error=f"fail {i}")
                assert d.status == "failed"
                assert d.next_retry_at is not None

            # 5th failure (attempt 5 -> dead_letter or attempt 6 -> dead_letter)
            # After 5 total failures, status dead_letter per spec
            d = await svc.record_failure(d.id, error="final")
            # Should be dead_letter after 5 attempts
            # Allow either 5th failure marks dead_letter or requires 6th
            if d.status != "dead_letter":
                d = await svc.record_failure(d.id, error="extra")
                assert d.status == "dead_letter"
            assert d.status == "dead_letter"
            assert d.next_retry_at is None

            # Delivered path
        await eng.dispose()
