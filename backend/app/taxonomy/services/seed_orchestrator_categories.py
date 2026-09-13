"""Seed script for orchestrator category associations — HU-T11."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import (
    Orchestrator,
    Category,
    OrchestratorCategory,
)


# Mapping of orchestrator slugs to category slugs
ORCHESTRATOR_CATEGORY_MAPPINGS = {
    "langchain": ["tool_use", "workflow", "rag"],
    "llamaindex": ["rag", "memory", "tool_use"],
    "autogen": ["multi_agent", "planning", "workflow"],
    "crewai": ["multi_agent", "planning", "workflow"],
    "semantic-kernel": ["tool_use", "planning", "memory"],
    "haystack": ["rag", "workflow", "evaluation"],
    "dspy": ["evaluation", "planning", "routing"],
    "gentle-orchestrator": ["multi_agent", "tool_use", "planning", "workflow", "observability"],
}

ORCHESTRATOR_TAXONOMY_VERSION = "orchestrators-v1"


async def seed_orchestrator_category_associations(session: AsyncSession) -> dict:
    """Seed orchestrator category associations into the database.

    Returns:
        Dict with counts of created/skipped items.
    """
    created = 0
    skipped = 0

    for orch_slug, cat_slugs in ORCHESTRATOR_CATEGORY_MAPPINGS.items():
        # Get orchestrator
        orch_result = await session.execute(
            select(Orchestrator).where(Orchestrator.slug == orch_slug)
        )
        orchestrator = orch_result.scalars().first()
        if not orchestrator:
            continue

        for cat_slug in cat_slugs:
            # Get category
            cat_result = await session.execute(
                select(Category).where(
                    Category.slug == cat_slug,
                    Category.taxonomy_version == ORCHESTRATOR_TAXONOMY_VERSION,
                )
            )
            category = cat_result.scalars().first()
            if not category:
                continue

            # Check if association already exists
            existing = await session.execute(
                select(OrchestratorCategory).where(
                    OrchestratorCategory.orchestrator_id == orchestrator.id,
                    OrchestratorCategory.category_id == category.id,
                )
            )
            if existing.scalars().first():
                skipped += 1
                continue

            # Create association
            now = datetime.now(UTC)
            assoc = OrchestratorCategory(
                orchestrator_id=orchestrator.id,
                category_id=category.id,
                taxonomy_version=ORCHESTRATOR_TAXONOMY_VERSION,
                created_at=now,
            )
            session.add(assoc)
            created += 1

    await session.commit()

    return {
        "associations_created": created,
        "associations_skipped": skipped,
    }
