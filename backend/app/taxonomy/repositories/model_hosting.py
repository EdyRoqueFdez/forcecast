"""ModelHosting Repository — CRUD + primary constraint atomic swap."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import ModelHosting
from app.taxonomy.services.core import DomainError


class ModelHostingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, model_id: str, provider_id: str, **kwargs) -> ModelHosting:
        hosting = ModelHosting(
            id=str(uuid.uuid4()),
            model_id=model_id,
            provider_id=provider_id,
            endpoint_url=kwargs.get("endpoint_url"),
            status=kwargs.get("status", "active"),
            is_primary=kwargs.get("is_primary", False),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(hosting)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(hosting)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("ModelHosting conflict (duplicate pair or primary)", status_code=409) from e
        return hosting

    async def get(self, hosting_id: str) -> ModelHosting | None:
        result = await self.session.execute(select(ModelHosting).where(ModelHosting.id == hosting_id))
        return result.scalar_one_or_none()

    async def list_by_model(self, model_id: str) -> list[ModelHosting]:
        result = await self.session.execute(select(ModelHosting).where(ModelHosting.model_id == model_id))
        return list(result.scalars().all())

    async def update(self, hosting: ModelHosting, **kwargs) -> ModelHosting:
        for key, value in kwargs.items():
            setattr(hosting, key, value)
        hosting.updated_at = datetime.now(UTC)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(hosting)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("ModelHosting update conflict", status_code=409) from e
        return hosting

    async def delete(self, hosting: ModelHosting) -> None:
        await self.session.delete(hosting)
        await self.session.flush()
        await self.session.commit()

    async def set_primary(self, model_id: str, hosting_id: str) -> ModelHosting:
        # Verify hosting exists and belongs to model
        result = await self.session.execute(
            select(ModelHosting).where(ModelHosting.id == hosting_id, ModelHosting.model_id == model_id)
        )
        target = result.scalar_one_or_none()
        if not target:
            raise DomainError(f"Hosting {hosting_id} not found for model {model_id}", status_code=404)

        # Atomic swap: unset previous primary, set new primary in same transaction
        # Use transaction: we already have session; do two updates then commit
        try:
            # Unset previous primaries for this model
            await self.session.execute(
                update(ModelHosting)
                .where(ModelHosting.model_id == model_id, ModelHosting.is_primary == True)  # noqa: E712
                .values(is_primary=False, updated_at=datetime.now(UTC))
            )
            # Set target to primary
            await self.session.execute(
                update(ModelHosting)
                .where(ModelHosting.id == hosting_id)
                .values(is_primary=True, updated_at=datetime.now(UTC))
            )
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(target)
            # Ensure target now shows primary
            result2 = await self.session.execute(select(ModelHosting).where(ModelHosting.id == hosting_id))
            refreshed = result2.scalar_one()
            return refreshed
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("Primary hosting conflict", status_code=409) from e
