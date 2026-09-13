"""Phase 5 — Ingestion Integration Tests (TDD RED).

Covers:
5.1 Ingestion Service Orchestration — run lifecycle, batched upsert, advisory lock, partial failure
5.5 Full integration: real DB (sqlite in-mem), mocked HTTP, idempotency, lock contention
"""

import asyncio
import hashlib
import json
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import event, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import TaxonomyVersion, IngestionSource, Provider, AIModel
from app.taxonomy.services.core import DomainError


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(eng.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.execute(sa_text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as s:
        # seed current version for FK
        v = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(v)
        # seed ingestion sources
        for code, name, parser in [
            ("openrouter", "OpenRouter", "OpenRouterParser"),
            ("huggingface", "Hugging Face", "HuggingFaceParser"),
            ("lmsys", "LMSYS Arena", "LMSYSParser"),
        ]:
            src = IngestionSource(code=code, name=name, parser_class=parser, rate_limit_rpm=60, base_url=f"https://example.com/{code}")
            s.add(src)
        # seed a provider for FK
        prov = Provider(slug="openai", name="OpenAI", status="active")
        s.add(prov)
        prov2 = Provider(slug="anthropic", name="Anthropic", status="active")
        s.add(prov2)
        await s.commit()
        yield s
        await s.rollback()


# ---------------------------------------------------------------------------
# 5.1 Orchestration — run lifecycle
# ---------------------------------------------------------------------------
class TestIngestionOrchestration:
    @pytest.mark.asyncio
    async def test_orchestration_success(self, session):
        from app.taxonomy.services.ingestion import IngestionService

        # Mock parser to return 2 models
        mock_models = [
            {
                "provider_slug": "openai",
                "slug": "gpt-4o",
                "display_name": "GPT-4o",
                "modality": ["text"],
                "status": "draft",
                "source": "openrouter",
                "source_payload_hash": "hash-gpt4o-1",
                "context_window": 128000,
            },
            {
                "provider_slug": "anthropic",
                "slug": "claude-3-5-sonnet",
                "display_name": "Claude 3.5 Sonnet",
                "modality": ["text", "vision"],
                "status": "draft",
                "source": "openrouter",
                "source_payload_hash": "hash-claude-1",
                "context_window": 200000,
            },
        ]

        with patch("app.taxonomy.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = AsyncMock()
            mock_parser.fetch = AsyncMock(return_value={"data": []})
            mock_parser.transform = MagicMock(return_value=mock_models)
            mock_get_parser.return_value = mock_parser

            svc = IngestionService(session)
            run = await svc.run("openrouter")

            assert run.status in ("success", "partial")
            assert run.models_found == 2
            assert run.models_created == 2
            assert run.models_updated == 0
            assert run.models_skipped == 0
            assert run.finished_at is not None

            # Verify models persisted
            from sqlalchemy import select
            result = await session.execute(select(AIModel))
            all_models = result.scalars().all()
            assert len(all_models) == 2

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_abort(self, session):
        from app.taxonomy.services.ingestion import IngestionService

        # One valid, one invalid (missing display_name will cause validation error or DB error)
        mock_models = [
            {
                "provider_slug": "openai",
                "slug": "valid-model",
                "display_name": "Valid Model",
                "modality": ["text"],
                "status": "draft",
                "source": "openrouter",
                "source_payload_hash": "hash-valid",
            },
            {
                "provider_slug": "openai",
                "slug": "invalid-model",
                "display_name": "",  # empty display_name -> will be treated as error (validation)
                "modality": ["text"],
                "status": "draft",
                "source": "openrouter",
                "source_payload_hash": "hash-invalid",
            },
            {
                "provider_slug": "openai",
                "slug": "another-valid",
                "display_name": "Another Valid",
                "modality": ["text"],
                "status": "draft",
                "source": "openrouter",
                "source_payload_hash": "hash-valid2",
            },
        ]

        with patch("app.taxonomy.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = AsyncMock()
            mock_parser.fetch = AsyncMock(return_value={})
            mock_parser.transform = MagicMock(return_value=mock_models)
            mock_get_parser.return_value = mock_parser

            svc = IngestionService(session)
            run = await svc.run("openrouter")

            # Should be partial — 2 succeeded, 1 failed
            assert run.status == "partial"
            assert run.models_found == 3
            assert run.models_created + run.models_updated >= 2
            assert run.models_skipped == 1 or len(run.errors or []) == 1
            assert run.errors is not None and len(run.errors) == 1
            assert run.errors[0]["model_slug"] == "invalid-model"

            # Successful models should still be persisted
            from sqlalchemy import select
            result = await session.execute(select(AIModel).where(AIModel.slug == "valid-model"))
            assert result.scalar_one_or_none() is not None
            result2 = await session.execute(select(AIModel).where(AIModel.slug == "another-valid"))
            assert result2.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_batch_size_500(self, session):
        from app.taxonomy.services.ingestion import IngestionService

        # Create 600 models to verify batching (batch size 500 per spec)
        mock_models = [
            {
                "provider_slug": "openai",
                "slug": f"model-{i}",
                "display_name": f"Model {i}",
                "modality": ["text"],
                "status": "draft",
                "source": "openrouter",
                "source_payload_hash": f"hash-{i}",
            }
            for i in range(600)
        ]

        with patch("app.taxonomy.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = AsyncMock()
            mock_parser.fetch = AsyncMock(return_value={})
            mock_parser.transform = MagicMock(return_value=mock_models)
            mock_get_parser.return_value = mock_parser

            svc = IngestionService(session)
            run = await svc.run("openrouter")
            assert run.models_found == 600
            assert run.models_created == 600
            assert run.status == "success"


# ---------------------------------------------------------------------------
# 5.5 Integration — idempotency, lock contention
# ---------------------------------------------------------------------------
class TestIngestionIntegration:
    @pytest.mark.asyncio
    async def test_idempotency_second_run_no_duplicates(self, session):
        from app.taxonomy.services.ingestion import IngestionService
        from sqlalchemy import select

        mock_models = [
            {
                "provider_slug": "openai",
                "slug": "gpt-4o",
                "display_name": "GPT-4o",
                "modality": ["text"],
                "status": "draft",
                "source": "openrouter",
                "source_payload_hash": "hash-idem-1",
            }
        ]

        with patch("app.taxonomy.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = AsyncMock()
            mock_parser.fetch = AsyncMock(return_value={})
            mock_parser.transform = MagicMock(return_value=mock_models)
            mock_get_parser.return_value = mock_parser

            svc = IngestionService(session)
            run1 = await svc.run("openrouter")
            assert run1.models_created == 1
            assert run1.models_updated == 0

            # Second run with identical data
            run2 = await svc.run("openrouter")
            assert run2.models_created == 0
            assert run2.models_updated == 1

            # Total count unchanged
            result = await session.execute(select(AIModel))
            assert len(result.scalars().all()) == 1

    @pytest.mark.asyncio
    async def test_lock_contention_same_source_409(self, session):
        from app.taxonomy.services.ingestion import IngestionService
        from app.taxonomy.repositories.ingestion import IngestionRepository

        # Manually acquire lock, then try to run ingestion for same source
        repo = IngestionRepository(session)
        await repo.acquire_lock("openrouter")

        svc = IngestionService(session)
        with patch("app.taxonomy.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = AsyncMock()
            mock_parser.fetch = AsyncMock(return_value={})
            mock_parser.transform = MagicMock(return_value=[])
            mock_get_parser.return_value = mock_parser

            with pytest.raises(DomainError) as exc:
                await svc.run("openrouter")
            assert exc.value.status_code == 409

        await repo.release_lock("openrouter")

    @pytest.mark.asyncio
    async def test_different_sources_allowed_concurrently(self, session):
        from app.taxonomy.services.ingestion import IngestionService
        from app.taxonomy.repositories.ingestion import IngestionRepository

        repo = IngestionRepository(session)
        await repo.acquire_lock("openrouter")

        # Running huggingface while openrouter locked should succeed
        mock_models = [
            {
                "provider_slug": "openai",
                "slug": "hf-model",
                "display_name": "HF Model",
                "modality": ["text"],
                "status": "draft",
                "source": "huggingface",
                "source_payload_hash": "hash-hf-1",
            }
        ]
        with patch("app.taxonomy.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = AsyncMock()
            mock_parser.fetch = AsyncMock(return_value=[])
            mock_parser.transform = MagicMock(return_value=mock_models)
            mock_get_parser.return_value = mock_parser

            svc = IngestionService(session)
            run = await svc.run("huggingface")
            assert run.status == "success"
            assert run.models_created == 1

        await repo.release_lock("openrouter")
        # Cleanup: release any remaining
        try:
            await repo.release_lock("huggingface")
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_run_tracks_counts_and_errors_jsonb(self, session):
        from app.taxonomy.services.ingestion import IngestionService
        from sqlalchemy import select
        from app.taxonomy.models.entities import IngestionRun

        mock_models = [
            {
                "provider_slug": "openai",
                "slug": "ok-model",
                "display_name": "OK",
                "modality": ["text"],
                "status": "draft",
                "source": "lmsys",
                "source_payload_hash": "hash-ok",
            }
        ]
        with patch("app.taxonomy.services.ingestion.get_parser") as mock_get_parser:
            mock_parser = AsyncMock()
            mock_parser.fetch = AsyncMock(return_value={})
            mock_parser.transform = MagicMock(return_value=mock_models)
            mock_get_parser.return_value = mock_parser

            svc = IngestionService(session)
            run = await svc.run("lmsys")
            # Verify run persisted with counts
            result = await session.execute(select(IngestionRun).where(IngestionRun.id == run.id))
            persisted = result.scalar_one()
            assert persisted.models_found == 1
            assert persisted.models_created == 1
            assert persisted.status == "success"
            assert persisted.finished_at is not None
