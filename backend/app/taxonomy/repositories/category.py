"""Category Repository — tree ops, translations, cycle detection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import Category, CategoryTranslation
from app.taxonomy.services.core import DomainError, normalize_slug


class CategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, slug: str, taxonomy_version: str, **kwargs) -> Category:
        normalized = normalize_slug(slug)
        parent_id = kwargs.get("parent_id")
        # Validate parent exists and same version
        if parent_id:
            result = await self.session.execute(select(Category).where(Category.id == parent_id))
            parent = result.scalar_one_or_none()
            if not parent:
                raise DomainError(f"Parent category {parent_id} not found", status_code=404)
            if parent.taxonomy_version != taxonomy_version:
                raise DomainError("Parent must be in same taxonomy_version", status_code=409)
            # Cycle check: ensure parent is not descendant of new node (new node has no descendants yet, so just prevent self)
            if parent_id == normalized:
                raise DomainError("Cycle detected", status_code=409)
            # depth check: max 2 (root + 1 child)
            if parent.parent_id is not None:
                raise DomainError("Max depth 2 exceeded", status_code=409)

        cat = Category(
            id=str(uuid.uuid4()),
            slug=normalized,
            parent_id=parent_id,
            taxonomy_version=taxonomy_version,
            status=kwargs.get("status", "active"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(cat)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(cat)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError(f"Category slug conflict: {slug} in version {taxonomy_version}", status_code=409) from e
        return cat

    async def get(self, category_id: str) -> Category | None:
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    async def list(self, taxonomy_version: str | None = None) -> list[Category]:
        stmt = select(Category)
        if taxonomy_version:
            stmt = stmt.where(Category.taxonomy_version == taxonomy_version)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_children(self, parent_id: str) -> list[Category]:
        result = await self.session.execute(select(Category).where(Category.parent_id == parent_id))
        return list(result.scalars().all())

    async def update(self, category_id: str, **kwargs) -> Category:
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        cat = result.scalar_one_or_none()
        if not cat:
            raise DomainError(f"Category {category_id} not found", status_code=404)

        new_parent_id = kwargs.get("parent_id")
        if new_parent_id is not None:
            # Check cycle: walk ancestors of new_parent
            if new_parent_id == category_id:
                raise DomainError("Cycle: category cannot be parent of itself", status_code=409)
            visited = set()
            current_id = new_parent_id
            while current_id:
                if current_id == category_id:
                    raise DomainError("Cycle detected", status_code=409)
                if current_id in visited:
                    break
                visited.add(current_id)
                res = await self.session.execute(select(Category).where(Category.id == current_id))
                parent = res.scalar_one_or_none()
                if not parent:
                    raise DomainError(f"Parent {current_id} not found", status_code=404)
                if parent.taxonomy_version != cat.taxonomy_version:
                    raise DomainError("Parent must be same taxonomy_version", status_code=409)
                current_id = parent.parent_id
                # prevent depth >2
                if len(visited) > 2:
                    raise DomainError("Max depth exceeded", status_code=409)
            cat.parent_id = new_parent_id

        if "slug" in kwargs and kwargs["slug"]:
            cat.slug = normalize_slug(kwargs["slug"])
        if "status" in kwargs:
            cat.status = kwargs["status"]
        cat.updated_at = datetime.now(UTC)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(cat)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("Category update conflict", status_code=409) from e
        return cat

    async def delete(self, category_id: str) -> None:
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        cat = result.scalar_one_or_none()
        if not cat:
            raise DomainError(f"Category {category_id} not found", status_code=404)
        # Check children
        children = await self.list_children(category_id)
        if children:
            raise DomainError("Cannot delete parent with children (RESTRICT)", status_code=409)
        try:
            await self.session.delete(cat)
            await self.session.flush()
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError("Cannot delete category with dependencies", status_code=409) from e

    async def upsert_translation(
        self, category_id: str, locale: str, name: str, description: str | None = None
    ) -> CategoryTranslation:
        locale_str = str(locale).lower() if hasattr(locale, "value") else str(locale).lower()
        result = await self.session.execute(
            select(CategoryTranslation).where(
                CategoryTranslation.category_id == category_id,
                CategoryTranslation.locale == locale_str,
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
        trans = CategoryTranslation(
            id=str(uuid.uuid4()),
            category_id=category_id,
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
            raise DomainError(f"Category translation conflict for {locale_str}", status_code=409) from e
        return trans
