"""Provider Repository — CRUD + translation upsert."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import Provider, ProviderTranslation
from app.taxonomy.services.core import DomainError, normalize_slug


class ProviderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, slug: str, name: str, **kwargs) -> Provider:
        normalized = normalize_slug(slug) if slug else slug
        provider = Provider(
            id=str(uuid.uuid4()),
            slug=normalized,
            name=name,
            status=kwargs.get("status", "active"),
            website=kwargs.get("website"),
            api_docs_url=kwargs.get("api_docs_url"),
            logo_url=kwargs.get("logo_url"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(provider)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(provider)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError(f"Provider slug already exists: {slug}", status_code=409) from e
        return provider

    async def get(self, provider_id: str) -> Provider | None:
        result = await self.session.execute(select(Provider).where(Provider.id == provider_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Provider | None:
        normalized = normalize_slug(slug)
        result = await self.session.execute(select(Provider).where(Provider.slug == normalized))
        return result.scalar_one_or_none()

    async def list(self, status: str | None = None) -> list[Provider]:
        stmt = select(Provider)
        if status:
            stmt = stmt.where(Provider.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, provider: Provider, **kwargs) -> Provider:
        for key, value in kwargs.items():
            if key == "slug" and value:
                value = normalize_slug(value)
            setattr(provider, key, value)
        provider.updated_at = datetime.now(UTC)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(provider)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("Provider update conflict", status_code=409) from e
        return provider

    async def delete(self, provider: Provider) -> None:
        try:
            await self.session.delete(provider)
            await self.session.flush()
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("Cannot delete provider with associated models", status_code=409) from e

    async def upsert_translation(
        self, provider_id: str, locale: str, name: str, description: str | None = None
    ) -> ProviderTranslation:
        # Normalize locale to string value
        locale_str = str(locale).lower() if hasattr(locale, "value") else str(locale).lower()
        # Try find existing
        result = await self.session.execute(
            select(ProviderTranslation).where(
                ProviderTranslation.provider_id == provider_id,
                ProviderTranslation.locale == locale_str,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = name
            if description is not None:
                existing.description = description
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        # create new
        trans = ProviderTranslation(
            id=str(uuid.uuid4()),
            provider_id=provider_id,
            locale=locale_str,
            name=name,
            description=description,
        )
        self.session.add(trans)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(trans)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError(f"Translation conflict for locale {locale_str}", status_code=409) from e
        return trans
