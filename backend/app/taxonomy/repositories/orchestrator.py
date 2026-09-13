"""Orchestrator repository — queries for orchestrator data."""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.taxonomy.models.entities import (
    Orchestrator,
    OrchestratorTranslation,
    OrchestratorProvider,
    Provider,
    ProviderTranslation,
)


class OrchestratorRepository:
    """Repository for orchestrator queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_approved(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        order: str = "asc",
    ) -> tuple[list[Orchestrator], int]:
        """List approved orchestrators with pagination.

        Returns:
            Tuple of (list of orchestrators, total count)
        """
        # Base query for approved orchestrators
        base_query = select(Orchestrator).where(Orchestrator.status == "approved")

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        result = await self.session.execute(count_query)
        total = result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Orchestrator, sort, Orchestrator.name)
        if order == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        # Apply pagination
        query = (
            base_query
            .options(selectinload(Orchestrator.translations))
            .order_by(sort_column)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        orchestrators = list(result.scalars().all())

        return orchestrators, total

    async def get_by_slug(self, slug: str) -> Orchestrator | None:
        """Get orchestrator by slug with translations."""
        query = (
            select(Orchestrator)
            .where(Orchestrator.slug == slug, Orchestrator.status == "approved")
            .options(selectinload(Orchestrator.translations))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_providers(
        self, orchestrator_ids: list[str]
    ) -> dict[str, list[dict]]:
        """Batch fetch providers for orchestrators.

        Returns:
            Dict mapping orchestrator_id to list of provider dicts
        """
        if not orchestrator_ids:
            return {}

        query = (
            select(OrchestratorProvider, Provider, ProviderTranslation)
            .join(Provider, OrchestratorProvider.provider_id == Provider.id)
            .outerjoin(
                ProviderTranslation,
                (ProviderTranslation.provider_id == Provider.id)
                & (ProviderTranslation.locale == "en")
            )
            .where(OrchestratorProvider.orchestrator_id.in_(orchestrator_ids))
        )

        result = await self.session.execute(query)
        rows = result.all()

        # Group by orchestrator_id
        providers_map: dict[str, list[dict]] = {}
        for op, provider, translation in rows:
            if op.orchestrator_id not in providers_map:
                providers_map[op.orchestrator_id] = []
            providers_map[op.orchestrator_id].append({
                "id": provider.id,
                "slug": provider.slug,
                "name": translation.name if translation else provider.name,
            })

        return providers_map
