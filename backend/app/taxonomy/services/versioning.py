"""Taxonomy Versioning Service — create, activate, tree copy, immutability."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.taxonomy.models.entities import Category, CategoryTranslation, TaxonomyVersion
from app.taxonomy.services.core import DomainError


class VersioningService:
    def __init__(self, session):
        self.session = session

    async def get_current(self) -> TaxonomyVersion | None:
        result = await self.session.execute(select(TaxonomyVersion).where(TaxonomyVersion.is_current == True))  # noqa: E712
        return result.scalar_one_or_none()

    async def create_version(self, version: str, notes: str | None = None) -> TaxonomyVersion:
        # Duplicate check
        existing = await self.session.execute(select(TaxonomyVersion).where(TaxonomyVersion.version == version))
        if existing.scalar_one_or_none():
            raise DomainError(f"TaxonomyVersion {version} already exists", status_code=409)
        # Determine current version to copy from
        current = await self.get_current()
        # Create new version row
        tv = TaxonomyVersion(
            id=str(uuid.uuid4()),
            version=version,
            released_at=datetime.now(UTC),
            notes=notes,
            is_current=False,
        )
        self.session.add(tv)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError(f"TaxonomyVersion {version} already exists", status_code=409) from e

        # Copy category tree if current exists
        if current:
            await self._copy_tree(current.version, version)

        try:
            await self.session.commit()
            await self.session.refresh(tv)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError(f"TaxonomyVersion {version} already exists", status_code=409) from e
        return tv

    async def _copy_tree(self, from_version: str, to_version: str) -> None:
        # Fetch all categories for from_version
        result = await self.session.execute(select(Category).where(Category.taxonomy_version == from_version))
        old_cats = result.scalars().all()
        if not old_cats:
            return
        # First pass: create new categories without parents
        old_to_new: dict[str, Category] = {}
        for old in old_cats:
            new_cat = Category(
                id=str(uuid.uuid4()),
                slug=old.slug,
                parent_id=None,
                taxonomy_version=to_version,
                status=old.status,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.session.add(new_cat)
            old_to_new[old.id] = new_cat
        await self.session.flush()
        # Second pass: fix parent_id mapping
        for old in old_cats:
            if old.parent_id:
                new_cat = old_to_new[old.id]
                new_parent = old_to_new.get(old.parent_id)
                if new_parent:
                    new_cat.parent_id = new_parent.id
        await self.session.flush()
        # Copy translations
        for old in old_cats:
            new_cat = old_to_new[old.id]
            trans_result = await self.session.execute(select(CategoryTranslation).where(CategoryTranslation.category_id == old.id))
            old_trans = trans_result.scalars().all()
            for t in old_trans:
                new_t = CategoryTranslation(
                    id=str(uuid.uuid4()),
                    category_id=new_cat.id,
                    locale=t.locale,
                    name=t.name,
                    description=t.description,
                )
                self.session.add(new_t)
        await self.session.flush()

    async def activate_version(self, version_id: str) -> TaxonomyVersion:
        result = await self.session.execute(select(TaxonomyVersion).where(TaxonomyVersion.id == version_id))
        target = result.scalar_one_or_none()
        if not target:
            raise DomainError(f"TaxonomyVersion {version_id} not found", status_code=404)
        if target.is_current:
            return target
        # Atomic swap via updates
        from sqlalchemy import update as sa_update

        try:
            await self.session.execute(
                sa_update(TaxonomyVersion).where(TaxonomyVersion.is_current == True).values(is_current=False)  # noqa: E712
            )
            await self.session.execute(
                sa_update(TaxonomyVersion).where(TaxonomyVersion.id == version_id).values(is_current=True)
            )
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(target)
            # Reload to ensure current
            refreshed = await self.session.execute(select(TaxonomyVersion).where(TaxonomyVersion.id == version_id))
            return refreshed.scalar_one()
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("Version activation conflict", status_code=409) from e

    async def update_category(self, category_id: str, **kwargs) -> Category:
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        cat = result.scalar_one_or_none()
        if not cat:
            raise DomainError(f"Category {category_id} not found", status_code=404)
        current = await self.get_current()
        # Historical immutability: only current version is mutable
        if current and cat.taxonomy_version != current.version:
            raise DomainError(f"Cannot modify historical version {cat.taxonomy_version}", status_code=409)
        if not current and cat.taxonomy_version:
            # No current? allow? But block if cat not in any current
            pass
        # Apply updates
        if "slug" in kwargs and kwargs["slug"]:
            from app.taxonomy.services.core import normalize_slug

            cat.slug = normalize_slug(kwargs["slug"])
        if "status" in kwargs:
            cat.status = kwargs["status"]
        if "parent_id" in kwargs:
            cat.parent_id = kwargs["parent_id"]
        cat.updated_at = datetime.now(UTC)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(cat)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("Category update conflict", status_code=409) from e
        return cat
