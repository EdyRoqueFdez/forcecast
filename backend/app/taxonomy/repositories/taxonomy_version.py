"""TaxonomyVersion Repository — version lifecycle + atomic activation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import TaxonomyVersion
from app.taxonomy.services.core import DomainError


class TaxonomyVersionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, version: str, notes: str | None = None, is_current: bool = False) -> TaxonomyVersion:
        tv = TaxonomyVersion(
            id=str(uuid.uuid4()),
            version=version,
            released_at=datetime.now(UTC),
            notes=notes,
            is_current=is_current,
        )
        self.session.add(tv)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(tv)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError(f"TaxonomyVersion {version} already exists or single current violation", status_code=409) from e
        return tv

    async def get(self, version_id: str) -> TaxonomyVersion | None:
        result = await self.session.execute(select(TaxonomyVersion).where(TaxonomyVersion.id == version_id))
        return result.scalar_one_or_none()

    async def get_by_version(self, version: str) -> TaxonomyVersion | None:
        result = await self.session.execute(select(TaxonomyVersion).where(TaxonomyVersion.version == version))
        return result.scalar_one_or_none()

    async def get_current(self) -> TaxonomyVersion | None:
        result = await self.session.execute(select(TaxonomyVersion).where(TaxonomyVersion.is_current == True))  # noqa: E712
        return result.scalar_one_or_none()

    async def list(self) -> list[TaxonomyVersion]:
        result = await self.session.execute(select(TaxonomyVersion))
        return list(result.scalars().all())

    async def activate(self, version_id: str) -> TaxonomyVersion:
        result = await self.session.execute(select(TaxonomyVersion).where(TaxonomyVersion.id == version_id))
        target = result.scalar_one_or_none()
        if not target:
            raise DomainError(f"TaxonomyVersion {version_id} not found", status_code=404)
        if target.is_current:
            return target  # idempotent
        # Atomic swap: unset all currents, set target
        try:
            await self.session.execute(
                update(TaxonomyVersion)
                .where(TaxonomyVersion.is_current == True)  # noqa: E712
                .values(is_current=False)
            )
            await self.session.execute(
                update(TaxonomyVersion).where(TaxonomyVersion.id == version_id).values(is_current=True)
            )
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(target)
            # verify single current
            refreshed = await self.get(version_id)
            return refreshed  # type: ignore
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("Version activation conflict", status_code=409) from e
