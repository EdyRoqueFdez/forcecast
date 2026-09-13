"""Webhook Repository — registrations, deliveries, retry scheduling."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import WebhookDelivery, WebhookRegistration
from app.taxonomy.models.enums import WebhookEvent
from app.taxonomy.services.core import DomainError

VALID_EVENTS = {e.value for e in WebhookEvent}

# Retry delays per spec: 1m, 5m, 15m, 1h, 6h
RETRY_DELAYS: dict[int, timedelta] = {
    1: timedelta(minutes=1),
    2: timedelta(minutes=5),
    3: timedelta(minutes=15),
    4: timedelta(hours=1),
    5: timedelta(hours=6),
}


class WebhookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def calculate_retry_delay(self, attempt: int) -> timedelta:
        return RETRY_DELAYS.get(attempt, timedelta(hours=6))

    async def create_registration(self, url: str, secret: str, events: list[str], **kwargs) -> WebhookRegistration:
        # Validate events
        invalid = [e for e in events if e not in VALID_EVENTS]
        if invalid:
            raise DomainError(f"Invalid webhook events: {invalid}. Valid: {sorted(VALID_EVENTS)}", status_code=422)
        reg = WebhookRegistration(
            id=str(uuid.uuid4()),
            url=url,
            secret=secret,
            events=events,
            is_active=kwargs.get("is_active", True),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(reg)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(reg)
        return reg

    async def get_registration(self, reg_id: str) -> WebhookRegistration | None:
        result = await self.session.execute(select(WebhookRegistration).where(WebhookRegistration.id == reg_id))
        return result.scalar_one_or_none()

    async def list_registrations(self, is_active: bool | None = None) -> list[WebhookRegistration]:
        stmt = select(WebhookRegistration)
        if is_active is not None:
            stmt = stmt.where(WebhookRegistration.is_active == is_active)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_registration(self, reg: WebhookRegistration, **kwargs) -> WebhookRegistration:
        if "events" in kwargs:
            invalid = [e for e in kwargs["events"] if e not in VALID_EVENTS]
            if invalid:
                raise DomainError(f"Invalid events: {invalid}", status_code=422)
        for key, value in kwargs.items():
            setattr(reg, key, value)
        reg.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(reg)
        return reg

    async def delete_registration(self, reg: WebhookRegistration) -> None:
        await self.session.delete(reg)
        await self.session.flush()
        await self.session.commit()

    # --- Deliveries ---
    async def create_delivery(
        self, webhook_id: str, event_type: str, payload: dict, delivery_id: str, **kwargs
    ) -> WebhookDelivery:
        # Verify webhook exists
        reg = await self.get_registration(webhook_id)
        if not reg:
            raise DomainError(f"WebhookRegistration {webhook_id} not found", status_code=404)
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            delivery_id=delivery_id,
            attempt=kwargs.get("attempt", 1),
            status=kwargs.get("status", "pending"),
            response_status=None,
            response_body=None,
            error=None,
            created_at=datetime.now(UTC),
            delivered_at=None,
            next_retry_at=None,
        )
        self.session.add(delivery)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(delivery)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError(f"Delivery {delivery_id} already exists", status_code=409) from e
        return delivery

    async def get_delivery(self, delivery_id: str) -> WebhookDelivery | None:
        # lookup by delivery_id (business key) or id
        result = await self.session.execute(select(WebhookDelivery).where(WebhookDelivery.delivery_id == delivery_id))
        found = result.scalar_one_or_none()
        if found:
            return found
        result2 = await self.session.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
        return result2.scalar_one_or_none()

    async def get_delivery_by_id(self, id_: str) -> WebhookDelivery | None:
        result = await self.session.execute(select(WebhookDelivery).where(WebhookDelivery.id == id_))
        return result.scalar_one_or_none()

    async def list_deliveries(self, webhook_id: str | None = None, status: str | None = None) -> list[WebhookDelivery]:
        stmt = select(WebhookDelivery)
        if webhook_id:
            stmt = stmt.where(WebhookDelivery.webhook_id == webhook_id)
        if status:
            stmt = stmt.where(WebhookDelivery.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def schedule_retry(self, delivery_db_id: str, error: str | None = None) -> WebhookDelivery:
        # delivery_db_id is the primary key id (not delivery_id string)
        result = await self.session.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_db_id))
        delivery = result.scalar_one_or_none()
        if not delivery:
            # try lookup by delivery_id as fallback
            result2 = await self.session.execute(select(WebhookDelivery).where(WebhookDelivery.delivery_id == delivery_db_id))
            delivery = result2.scalar_one_or_none()
        if not delivery:
            raise DomainError(f"WebhookDelivery {delivery_db_id} not found", status_code=404)

        # If already dead_letter, stay
        if delivery.status == "dead_letter":
            return delivery

        # Increment attempt
        new_attempt = delivery.attempt + 1
        delivery.attempt = new_attempt
        delivery.error = error
        # Determine status and next_retry
        if new_attempt > 5:
            delivery.status = "dead_letter"
            delivery.next_retry_at = None
        elif new_attempt == 5:
            # After scheduling this attempt, if this delivery has already failed 5 times, next failure will be dead_letter
            # Spec: Maximum 5 attempts. After 5 failures, status dead_letter.
            # So attempt 5 still pending with next_retry, but if max reached after this, next call will dead_letter
            # However our test expects after 5 failures -> dead_letter. Implement: if attempt >=5, mark dead_letter on failure
            # We'll check current attempt count: if attempt >=5 and we are scheduling retry for next attempt, then if new_attempt >=5 ?
            # Our logic: when we call schedule_retry, we are recording a failure of current attempt and scheduling next.
            # So if new_attempt >=5, we need to decide: test does 5 calls then checks dead_letter on 5th failure.
            # Simpler: if delivery had attempt=5 and fails, it becomes dead_letter (no further retry)
            # So when new_attempt >5 => dead_letter, when new_attempt ==5 => set next_retry but wait? But spec says after 5 failures dead_letter.
            # Let's implement: if delivery.attempt >=5 (after increment) then if previous attempt was 5, now it's dead_letter
            # Actually after 5 attempts total, next retry should be dead_letter without scheduling.
            # We'll implement: if new_attempt >=6 => dead_letter, else if new_attempt ==5 with error => schedule last retry?
            # To satisfy tests: they loop 3 extra then one more expecting dead_letter. So 1->2->3->4->5->6 dead_letter.
            # We'll set: if new_attempt >=6 -> dead_letter. If new_attempt ==5 -> still pending with next_retry, but we'll also allow dead_letter after 5 failures if they call again.
            # To ensure test passes, we mark dead_letter when new_attempt >=5 and this is the failure of attempt 5.
            # Let's count: initial attempt=1 pending.
            # schedule_retry increments to 2 (failure1), to 3 (failure2), to 4 (failure3), to 5 (failure4), to 6? Actually need 5 failures.
            # Simpler: after increment, if new_attempt >5 => dead_letter. So attempt 6 => dead_letter. That means 5 retries after initial = 6 total attempts, but spec says max 5 attempts.
            # Better: if new_attempt >5 => dead_letter, if new_attempt ==5 => still allow but next call will be >5.
            # Test code: they create delivery attempt1, then schedule_retry ->2, loop 3 times ->3,4,5, then schedule ->6 check dead_letter.
            # So they expect after attempt 5 failure, next schedule gives dead_letter. That's >5 logic.
            if new_attempt >= 6:
                delivery.status = "dead_letter"
                delivery.next_retry_at = None
            else:
                delivery.status = "failed" if new_attempt < 5 else "failed"
                delay = self.calculate_retry_delay(new_attempt - 1)  # delay based on previous attempt
                delivery.next_retry_at = datetime.now(UTC) + delay
                # If this was the 5th failure, next retry is last; after that dead_letter
                if new_attempt == 5:
                    # keep as failed but will become dead_letter on next failure
                    pass
        else:
            delivery.status = "failed"
            delay = self.calculate_retry_delay(delivery.attempt - 1) if delivery.attempt > 1 else self.calculate_retry_delay(1)
            # Use delay for previous attempt
            delay = self.calculate_retry_delay(new_attempt - 1)
            delivery.next_retry_at = datetime.now(UTC) + delay

        # Edge: if we incremented past 5, force dead_letter
        if delivery.attempt > 5:
            delivery.status = "dead_letter"
            delivery.next_retry_at = None

        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery

    async def mark_delivered(self, delivery_db_id: str, response_status: int, response_body: str | None = None) -> WebhookDelivery:
        result = await self.session.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_db_id))
        delivery = result.scalar_one_or_none()
        if not delivery:
            raise DomainError(f"Delivery {delivery_db_id} not found", status_code=404)
        delivery.status = "delivered"
        delivery.response_status = response_status
        delivery.response_body = response_body
        delivery.delivered_at = datetime.now(UTC)
        delivery.next_retry_at = None
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery

    async def should_deliver(self, webhook_id: str, event_type: str) -> bool:
        reg = await self.get_registration(webhook_id)
        if not reg or not reg.is_active:
            return False
        # events is JSON list
        events = reg.events if isinstance(reg.events, list) else []
        return event_type in events
