"""Ingestion Repository — sources, runs, advisory lock."""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import IngestionRun, IngestionSource
from app.taxonomy.services.core import DomainError

# In-memory advisory lock fallback for sqlite / tests
_advisory_locks: dict[str, bool] = {}
_lock_mutex = threading.Lock()


class IngestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Sources ---
    async def create_source(self, code: str, name: str, parser_class: str, **kwargs) -> IngestionSource:
        src = IngestionSource(
            code=code,
            name=name,
            parser_class=parser_class,
            rate_limit_rpm=kwargs.get("rate_limit_rpm", 60),
            base_url=kwargs.get("base_url"),
        )
        self.session.add(src)
        try:
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(src)
        except IntegrityError as e:
            await self.session.rollback()
            raise DomainError(f"IngestionSource {code} already exists", status_code=409) from e
        return src

    async def get_source(self, code: str) -> IngestionSource | None:
        result = await self.session.execute(select(IngestionSource).where(IngestionSource.code == code))
        return result.scalar_one_or_none()

    async def list_sources(self) -> list[IngestionSource]:
        result = await self.session.execute(select(IngestionSource))
        return list(result.scalars().all())

    # --- Runs ---
    async def create_run(self, source: str, **kwargs) -> IngestionRun:
        # Verify source exists
        src = await self.get_source(source)
        if not src:
            raise DomainError(f"IngestionSource {source} not found", status_code=404)
        run = IngestionRun(
            id=str(uuid.uuid4()),
            source=source,
            started_at=datetime.now(UTC),
            finished_at=None,
            status=kwargs.get("status", "running"),
            models_found=kwargs.get("models_found", 0),
            models_created=kwargs.get("models_created", 0),
            models_updated=kwargs.get("models_updated", 0),
            models_skipped=kwargs.get("models_skipped", 0),
            errors=kwargs.get("errors"),
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: str) -> IngestionRun | None:
        result = await self.session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
        return result.scalar_one_or_none()

    async def update_run_counts(self, run_id: str, **counts) -> IngestionRun:
        result = await self.session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            raise DomainError(f"IngestionRun {run_id} not found", status_code=404)
        for key, value in counts.items():
            if hasattr(run, key):
                setattr(run, key, value)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def finish_run(self, run_id: str, status: str = "success", errors: list | None = None) -> IngestionRun:
        result = await self.session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            raise DomainError(f"IngestionRun {run_id} not found", status_code=404)
        run.status = status
        run.finished_at = datetime.now(UTC)
        if errors is not None:
            run.errors = errors
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(run)
        return run

    # --- Advisory Lock ---
    async def acquire_lock(self, source_code: str) -> bool:
        # Try PG advisory lock via raw SQL if dialect supports it; fallback to in-memory
        try:
            # Attempt PG function; if fails, fallback
            # Use hash of source_code as lock key
            lock_key = abs(hash(source_code)) % 2147483647
            # Try to execute pg_try_advisory_xact_lock via text; on sqlite it will error
            from sqlalchemy import text as sa_text

            # Only try PG if engine is postgres
            bind = self.session.get_bind()
            dialect = bind.dialect.name if bind else "sqlite"
            if dialect == "postgresql":
                result = await self.session.execute(
                    sa_text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": lock_key}
                )
                acquired = result.scalar()
                if not acquired:
                    raise DomainError(f"Advisory lock busy for source {source_code}", status_code=409)
                return True
        except DomainError:
            raise
        except Exception:
            pass

        # In-memory fallback (for sqlite tests)
        with _lock_mutex:
            if _advisory_locks.get(source_code):
                raise DomainError(f"Advisory lock busy for source {source_code}", status_code=409)
            _advisory_locks[source_code] = True
        return True

    async def release_lock(self, source_code: str) -> None:
        # For PG, advisory xact lock is released at transaction end; no-op
        # For fallback, clear in-memory
        with _lock_mutex:
            _advisory_locks.pop(source_code, None)
        # Also try to release PG advisory if held (optional)
        try:
            from sqlalchemy import text as sa_text

            bind = self.session.get_bind()
            dialect = bind.dialect.name if bind else "sqlite"
            if dialect == "postgresql":
                lock_key = abs(hash(source_code)) % 2147483647
                await self.session.execute(sa_text("SELECT pg_advisory_unlock(:k)"), {"k": lock_key})
                await self.session.commit()
        except Exception:
            pass
