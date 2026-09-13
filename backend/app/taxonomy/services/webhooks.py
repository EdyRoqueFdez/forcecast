"""Webhook Service — HMAC signing, envelope, headers, retry, filtering + delivery."""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import WebhookDelivery, WebhookRegistration
from app.taxonomy.repositories.webhook import RETRY_DELAYS, WebhookRepository

# ---------------------------------------------------------------------------
# Pure helpers (deterministic, easy to test)
# ---------------------------------------------------------------------------

def sign_payload(secret: str, body: bytes) -> str:
    """HMAC-SHA256 hex digest of body using secret."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    """Constant-time compare of expected HMAC vs provided."""
    expected = sign_payload(secret, body)
    return hmac.compare_digest(expected, signature)


def build_envelope(event_type: str, data: dict, taxonomy_version: str) -> dict:
    """Build webhook payload envelope."""
    return {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "taxonomy_version": taxonomy_version,
        "data": data,
    }


def build_headers(secret: str, body: bytes, delivery_id: str) -> dict[str, str]:
    """Build X-Forcecast-* headers for delivery."""
    sig = sign_payload(secret, body)
    ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {
        "X-Forcecast-Signature": sig,
        "X-Forcecast-Delivery-Id": delivery_id,
        "X-Forcecast-Timestamp": ts,
        "Content-Type": "application/json",
    }


def get_retry_delay(attempt: int) -> timedelta:
    """Return delay for given attempt (1-indexed). Beyond 5 returns 6h."""
    return RETRY_DELAYS.get(attempt, RETRY_DELAYS[5])


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class WebhookService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = WebhookRepository(session)

    async def register(self, url: str, secret: str, events: list[str], **kwargs) -> WebhookRegistration:
        return await self.repo.create_registration(url=url, secret=secret, events=events, **kwargs)

    async def deactivate(self, reg_id: str) -> WebhookRegistration | None:
        reg = await self.repo.get_registration(reg_id)
        if not reg:
            return None
        return await self.repo.update_registration(reg, is_active=False)

    async def emit(self, event_type: str, data: dict, taxonomy_version: str = "v1") -> list[WebhookDelivery]:
        """Create deliveries for all active registrations matching event_type."""
        regs = await self.repo.list_registrations(is_active=True)
        deliveries: list[WebhookDelivery] = []
        for reg in regs:
            events = reg.events if isinstance(reg.events, list) else []
            if event_type not in events:
                continue
            envelope = build_envelope(event_type, data, taxonomy_version)
            payload_bytes = json.dumps(envelope, default=str).encode()
            delivery_id = str(uuid.uuid4())
            # Persist delivery
            delivery = await self.repo.create_delivery(
                webhook_id=reg.id,
                event_type=event_type,
                payload=envelope,
                delivery_id=delivery_id,
                attempt=1,
                status="pending",
            )
            deliveries.append(delivery)
        return deliveries

    async def record_failure(self, delivery_id: str, error: str | None = None) -> WebhookDelivery:
        """Record failure and schedule retry or dead_letter."""
        # delivery_id here is the PK id (uuid), not business delivery_id string — repo handles both
        return await self.repo.schedule_retry(delivery_id, error=error)

    async def mark_delivered(self, delivery_id: str, response_status: int = 200, response_body: str | None = None) -> WebhookDelivery:
        return await self.repo.mark_delivered(delivery_id, response_status, response_body)

    def calculate_retry_delay(self, attempt: int) -> timedelta:
        return get_retry_delay(attempt)

    async def dispatch(self, delivery: WebhookDelivery) -> bool:
        """Dispatch single delivery via HTTP POST with HMAC headers. Returns True if delivered."""
        # Fetch registration for secret + url
        reg = await self.repo.get_registration(delivery.webhook_id)
        if not reg or not reg.is_active:
            return False
        body = json.dumps(delivery.payload, default=str).encode()
        headers = build_headers(reg.secret, body, delivery.delivery_id)
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(reg.url, content=body, headers=headers)
            if 200 <= resp.status_code < 300:
                await self.mark_delivered(delivery.id, resp.status_code, resp.text[:1000] if resp.text else None)
                return True
            else:
                await self.record_failure(delivery.id, error=f"HTTP {resp.status_code}: {resp.text[:500]}")
                return False
        except Exception as e:
            await self.record_failure(delivery.id, error=str(e)[:1000])
            return False
