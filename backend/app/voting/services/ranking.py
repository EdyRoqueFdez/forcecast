"""Ranking service — vote aggregation for model and orchestrator rankings."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import AIModel, Category, ModelTranslation, ModelCategory
from app.voting.models.user_vote import UserVote
from app.voting.models.vote_event import VoteEvent


# Cache (Redis with in-memory fallback) TTL 5 minutes
_cache: dict[str, tuple[any, float]] = {}
_TTL = 300  # 5 minutes


def _cache_get(key: str) -> any | None:
    val = _cache.get(key)
    if val is None:
        return None
    data, ts = val
    if time.time() - ts > _TTL:
        _cache.pop(key, None)
        return None
    return data


def _cache_set(key: str, value: any) -> None:
    _cache[key] = (value, time.time())


class RankingService:
    """Service for calculating rankings from votes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_vote_tendency(self, model_id: str, category_id: str) -> dict:
        """Calculate vote tendency for 7d and 30d.

        Args:
            model_id: Model ID.
            category_id: Category ID.

        Returns:
            Dict with 7d and 30d tendency.
        """
        now = datetime.now(UTC)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # Get votes in last 7 days
        result_7d = await self.session.execute(
            select(func.count(VoteEvent.id)).where(
                VoteEvent.target_id == model_id,
                VoteEvent.category_id == category_id,
                VoteEvent.target_type == "model",
                VoteEvent.created_at >= seven_days_ago,
            )
        )
        votes_7d = result_7d.scalar() or 0

        # Get votes in last 30 days
        result_30d = await self.session.execute(
            select(func.count(VoteEvent.id)).where(
                VoteEvent.target_id == model_id,
                VoteEvent.category_id == category_id,
                VoteEvent.target_type == "model",
                VoteEvent.created_at >= thirty_days_ago,
            )
        )
        votes_30d = result_30d.scalar() or 0

        # Calculate tendency (positive = growing, negative = declining)
        if votes_30d > 0:
            # Normalize 7d votes to 30d scale
            normalized_7d = votes_7d * (30 / 7)
            tendency = ((normalized_7d - votes_30d) / votes_30d) * 100
        else:
            tendency = 0.0

        return {
            "votes_7d": votes_7d,
            "votes_30d": votes_30d,
            "tendency_pct": round(tendency, 2),
        }

    async def get_model_ranking(
        self,
        category_slug: str,
        locale: str = "en",
        min_votes: int = 5,
        limit: int = 20,
        cursor: str | None = None,
        use_cache: bool = True,
    ) -> tuple[list[dict], int]:
        """Get model ranking for a category.

        Args:
            category_slug: Category slug to rank by
            locale: Locale for translations
            min_votes: Minimum votes required to appear
            limit: Number of results per page
            cursor: Cursor for pagination
            use_cache: Whether to use cache

        Returns:
            Tuple of (ranking items, total count)
        """
        # Cache key
        cache_key = f"ranking:models:{category_slug}:{locale}:{min_votes}:{limit}:{cursor}"
        if use_cache:
            cached = _cache_get(cache_key)
            if cached is not None:
                return cached

        # Get category
        cat_result = await self.session.execute(
            select(Category).where(Category.slug == category_slug)
        )
        category = cat_result.scalars().first()
        if not category:
            return ([], 0)

        # Get all user votes for this category
        votes_result = await self.session.execute(
            select(UserVote).where(
                UserVote.category_id == category.id,
                UserVote.target_type == "model",
            )
        )
        votes = list(votes_result.scalars().all())

        # Aggregate votes by model
        model_votes: dict[str, dict] = {}
        for vote in votes:
            model_id = vote.target_id
            if model_id not in model_votes:
                model_votes[model_id] = {
                    "model_id": model_id,
                    "raw_votes": 0,
                    "weighted_score": Decimal("0"),
                }
            model_votes[model_id]["raw_votes"] += 1
            model_votes[model_id]["weighted_score"] += vote.weight

        # Filter by minimum votes
        filtered_models = [
            data for data in model_votes.values()
            if data["raw_votes"] >= min_votes
        ]

        # Sort by weighted score descending
        filtered_models.sort(key=lambda x: x["weighted_score"], reverse=True)

        # Calculate total for percentage
        total_votes = sum(data["raw_votes"] for data in filtered_models)

        # Get model details and translations
        model_ids = [data["model_id"] for data in filtered_models]
        if not model_ids:
            return ([], 0)

        # Get models
        models_result = await self.session.execute(
            select(AIModel).where(AIModel.id.in_(model_ids))
        )
        models = {m.id: m for m in models_result.scalars().all()}

        # Get translations
        trans_result = await self.session.execute(
            select(ModelTranslation).where(
                ModelTranslation.model_id.in_(model_ids),
                ModelTranslation.locale == locale,
            )
        )
        translations = {t.model_id: t for t in trans_result.scalars().all()}

        # Get English fallback translations
        en_trans_result = await self.session.execute(
            select(ModelTranslation).where(
                ModelTranslation.model_id.in_(model_ids),
                ModelTranslation.locale == "en",
            )
        )
        en_translations = {t.model_id: t for t in en_trans_result.scalars().all()}

        # Build ranking items
        items: list[dict] = []
        for data in filtered_models:
            model_id = data["model_id"]
            model = models.get(model_id)
            if not model:
                continue

            # Get translation
            trans = translations.get(model_id)
            en_trans = en_translations.get(model_id)

            if trans:
                display_name = trans.display_name
                locale_used = locale
            elif en_trans:
                display_name = en_trans.display_name
                locale_used = "en"
            else:
                display_name = model.display_name
                locale_used = "en"

            # Calculate percentage
            percentage = (
                (data["raw_votes"] / total_votes * 100)
                if total_votes > 0
                else 0
            )

            # Calculate confidence (simplified: based on sample size)
            confidence = min(1.0, data["raw_votes"] / 100)

            # Get tendency (7d/30d)
            tendency = await self._get_vote_tendency(model_id, category.id)

            items.append({
                "model_id": model_id,
                "slug": model.slug,
                "display_name": display_name,
                "provider_id": model.provider_id,
                "raw_votes": data["raw_votes"],
                "weighted_score": float(data["weighted_score"]),
                "percentage": round(percentage, 2),
                "confidence": round(confidence, 2),
                "sample_size": data["raw_votes"],
                "locale_used": locale_used,
                "votes_7d": tendency["votes_7d"],
                "votes_30d": tendency["votes_30d"],
                "tendency_pct": tendency["tendency_pct"],
            })

        # Apply cursor pagination
        if cursor:
            try:
                import base64
                import json
                cursor_data = json.loads(base64.urlsafe_b64decode(cursor + "=="))
                cursor_model_id = cursor_data.get("model_id")
                if cursor_model_id:
                    start_idx = next(
                        (i for i, item in enumerate(items) if item["model_id"] == cursor_model_id),
                        len(items),
                    )
                    items = items[start_idx + 1:]
            except Exception:
                pass

        # Apply limit
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]

        # Calculate total count
        total = len(filtered_models)

        # Cache result
        result = (items, total)
        if use_cache:
            _cache_set(cache_key, result)

        return result

    async def get_orchestrator_ranking(
        self,
        category_slug: str,
        locale: str = "en",
        min_votes: int = 5,
        limit: int = 20,
        cursor: str | None = None,
        use_cache: bool = True,
    ) -> tuple[list[dict], int]:
        """Get orchestrator ranking for a category.

        Args:
            category_slug: Category slug to rank by
            locale: Locale for translations
            min_votes: Minimum votes required to appear
            limit: Number of results per page
            cursor: Cursor for pagination
            use_cache: Whether to use cache

        Returns:
            Tuple of (ranking items, total count)
        """
        from app.taxonomy.models.entities import (
            Orchestrator,
            OrchestratorTranslation,
            Category,
        )

        # Cache key
        cache_key = f"ranking:orchestrators:{category_slug}:{locale}:{min_votes}:{limit}:{cursor}"
        if use_cache:
            cached = _cache_get(cache_key)
            if cached is not None:
                return cached

        # Get category (orchestrator categories have taxonomy_version = 'orchestrators-v1')
        cat_result = await self.session.execute(
            select(Category).where(
                Category.slug == category_slug,
                Category.taxonomy_version == "orchestrators-v1",
            )
        )
        category = cat_result.scalars().first()
        if not category:
            return ([], 0)

        # Get all user votes for this category
        votes_result = await self.session.execute(
            select(UserVote).where(
                UserVote.category_id == category.id,
                UserVote.target_type == "orchestrator",
            )
        )
        votes = list(votes_result.scalars().all())

        # Aggregate votes by orchestrator
        orch_votes: dict[str, dict] = {}
        for vote in votes:
            orch_id = vote.target_id
            if orch_id not in orch_votes:
                orch_votes[orch_id] = {
                    "orchestrator_id": orch_id,
                    "raw_votes": 0,
                    "weighted_score": Decimal("0"),
                }
            orch_votes[orch_id]["raw_votes"] += 1
            orch_votes[orch_id]["weighted_score"] += vote.weight

        # Filter by minimum votes
        filtered_orchestrators = [
            data for data in orch_votes.values()
            if data["raw_votes"] >= min_votes
        ]

        # Sort by weighted score descending
        filtered_orchestrators.sort(key=lambda x: x["weighted_score"], reverse=True)

        # Calculate total for percentage
        total_votes = sum(data["raw_votes"] for data in filtered_orchestrators)

        # Get orchestrator details and translations
        orch_ids = [data["orchestrator_id"] for data in filtered_orchestrators]
        if not orch_ids:
            return ([], 0)

        # Get orchestrators
        orch_result = await self.session.execute(
            select(Orchestrator).where(Orchestrator.id.in_(orch_ids))
        )
        orchestrators = {o.id: o for o in orch_result.scalars().all()}

        # Get translations
        trans_result = await self.session.execute(
            select(OrchestratorTranslation).where(
                OrchestratorTranslation.orchestrator_id.in_(orch_ids),
                OrchestratorTranslation.locale == locale,
            )
        )
        translations = {t.orchestrator_id: t for t in trans_result.scalars().all()}

        # Get English fallback translations
        en_trans_result = await self.session.execute(
            select(OrchestratorTranslation).where(
                OrchestratorTranslation.orchestrator_id.in_(orch_ids),
                OrchestratorTranslation.locale == "en",
            )
        )
        en_translations = {t.orchestrator_id: t for t in en_trans_result.scalars().all()}

        # Build ranking items
        items: list[dict] = []
        for data in filtered_orchestrators:
            orch_id = data["orchestrator_id"]
            orch = orchestrators.get(orch_id)
            if not orch:
                continue

            # Get translation
            trans = translations.get(orch_id)
            en_trans = en_translations.get(orch_id)

            if trans:
                name = trans.name
                locale_used = locale
            elif en_trans:
                name = en_trans.name
                locale_used = "en"
            else:
                name = orch.name
                locale_used = "en"

            # Calculate percentage
            percentage = (
                (data["raw_votes"] / total_votes * 100)
                if total_votes > 0
                else 0
            )

            # Calculate confidence (simplified: based on sample size)
            confidence = min(1.0, data["raw_votes"] / 100)

            items.append({
                "orchestrator_id": orch_id,
                "slug": orch.slug,
                "name": name,
                "maintainer": orch.maintainer,
                "raw_votes": data["raw_votes"],
                "weighted_score": float(data["weighted_score"]),
                "percentage": round(percentage, 2),
                "confidence": round(confidence, 2),
                "sample_size": data["raw_votes"],
                "locale_used": locale_used,
            })

        # Apply cursor pagination
        if cursor:
            try:
                import base64
                import json
                cursor_data = json.loads(base64.urlsafe_b64decode(cursor + "=="))
                cursor_orch_id = cursor_data.get("orchestrator_id")
                if cursor_orch_id:
                    start_idx = next(
                        (i for i, item in enumerate(items) if item["orchestrator_id"] == cursor_orch_id),
                        len(items),
                    )
                    items = items[start_idx + 1:]
            except Exception:
                pass

        # Apply limit
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]

        # Calculate total count
        total = len(filtered_orchestrators)

        # Cache result
        result = (items, total)
        if use_cache:
            _cache_set(cache_key, result)

        return result
