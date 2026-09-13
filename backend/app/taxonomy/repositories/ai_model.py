"""AIModel Repository — deduplication upsert with 3 unique constraints, batched."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import AIModel
from app.taxonomy.services.core import DomainError, normalize_slug


class AIModelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, model_id: str) -> AIModel | None:
        result = await self.session.execute(select(AIModel).where(AIModel.id == model_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> AIModel | None:
        normalized = normalize_slug(slug)
        result = await self.session.execute(select(AIModel).where(AIModel.slug == normalized))
        return result.scalar_one_or_none()

    async def list(self, provider_id: str | None = None, status: str | None = None) -> list[AIModel]:
        stmt = select(AIModel)
        if provider_id:
            stmt = stmt.where(AIModel.provider_id == provider_id)
        if status:
            stmt = stmt.where(AIModel.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _find_existing(self, data: dict) -> AIModel | None:
        # 1. Check source_payload_hash (global unique, not empty)
        sph = data.get("source_payload_hash")
        if sph:
            result = await self.session.execute(select(AIModel).where(AIModel.source_payload_hash == sph))
            existing = result.scalar_one_or_none()
            if existing:
                return existing
        # 2. Check (provider_id, slug)
        provider_id = data.get("provider_id")
        slug = data.get("slug")
        if provider_id and slug:
            normalized = normalize_slug(slug)
            result = await self.session.execute(
                select(AIModel).where(AIModel.provider_id == provider_id, AIModel.slug == normalized)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
        # 3. Check (provider_id, family, version) when both present
        family = data.get("family")
        version = data.get("version")
        if provider_id and family and version:
            result = await self.session.execute(
                select(AIModel).where(
                    AIModel.provider_id == provider_id,
                    AIModel.family == family,
                    AIModel.version == version,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
        return None

    async def upsert(self, data: dict) -> tuple[AIModel, bool]:
        # data expects keys: provider_id, slug, display_name, etc.
        existing = await self._find_existing(data)
        if existing:
            # update fields (exclude id)
            for key, value in data.items():
                if key == "slug" and value:
                    value = normalize_slug(value)
                if key == "id":
                    continue
                setattr(existing, key, value)
            existing.updated_at = datetime.now(UTC)
            try:
                await self.session.flush()
                await self.session.commit()
                await self.session.refresh(existing)
            except IntegrityError as e:
                await self.session.rollback()
                raise DomainError("AIModel upsert conflict", status_code=409) from e
            return existing, False
        # create new
        slug_val = data.get("slug")
        if slug_val:
            data = dict(data)
            data["slug"] = normalize_slug(slug_val)
        model = AIModel(
            id=str(uuid.uuid4()),
            provider_id=data["provider_id"],
            slug=data["slug"],
            display_name=data["display_name"],
            family=data.get("family"),
            version=data.get("version"),
            modality=data.get("modality", []),
            context_window=data.get("context_window"),
            max_output_tokens=data.get("max_output_tokens"),
            input_price_per_mtok=data.get("input_price_per_mtok"),
            output_price_per_mtok=data.get("output_price_per_mtok"),
            release_date=data.get("release_date"),
            deprecation_date=data.get("deprecation_date"),
            status=data.get("status", "draft"),
            source=data.get("source", "manual"),
            source_payload_hash=data.get("source_payload_hash", ""),
            source_url=data.get("source_url"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(model)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(model)
        except IntegrityError as e:
            await self.session.rollback()
            # If race condition, try update again
            # Check if now exists via any constraint
            existing2 = await self._find_existing(data)
            if existing2:
                for key, value in data.items():
                    if key == "slug" and value:
                        value = normalize_slug(value)
                    if key == "id":
                        continue
                    setattr(existing2, key, value)
                existing2.updated_at = datetime.now(UTC)
                await self.session.flush()
                await self.session.commit()
                await self.session.refresh(existing2)
                return existing2, False
            raise DomainError("AIModel create conflict", status_code=409) from e
        return model, True

    async def upsert_batch(self, items: list[dict]) -> tuple[int, int]:
        created = 0
        updated = 0
        for item in items:
            _, is_created = await self.upsert(item)
            if is_created:
                created += 1
            else:
                updated += 1
        return created, updated

    async def delete(self, model: AIModel) -> None:
        await self.session.delete(model)
        await self.session.flush()
        await self.session.commit()
