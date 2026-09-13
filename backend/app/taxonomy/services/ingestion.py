"""Ingestion Service — orchestration, batched upsert, advisory lock, partial failure."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.repositories.ai_model import AIModelRepository
from app.taxonomy.repositories.ingestion import IngestionRepository
from app.taxonomy.repositories.provider import ProviderRepository
from app.taxonomy.services.core import DomainError

BATCH_SIZE = 500


def get_parser(parser_class: str, base_url: str | None = None, rate_limit_rpm: int = 60):
    """Factory resolving parser_class string to instance."""
    if parser_class == "OpenRouterParser":
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        return OpenRouterParser(base_url=base_url, rate_limit_rpm=rate_limit_rpm)
    if parser_class == "HuggingFaceParser":
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        return HuggingFaceParser(base_url=base_url, rate_limit_rpm=rate_limit_rpm)
    if parser_class == "LMSYSParser":
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        return LMSYSParser(base_url=base_url, rate_limit_rpm=rate_limit_rpm)
    raise DomainError(f"Unknown parser_class {parser_class}", status_code=422)


class IngestionService:
    """Orchestrates ingestion runs: lock → create run → fetch/transform → batched upsert → finish."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ingestion_repo = IngestionRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.model_repo = AIModelRepository(session)

    async def run(self, source_code: str) -> Any:
        # Acquire advisory lock (per source)
        await self.ingestion_repo.acquire_lock(source_code)

        # Resolve source
        source = await self.ingestion_repo.get_source(source_code)
        if not source:
            await self.ingestion_repo.release_lock(source_code)
            raise DomainError(f"IngestionSource {source_code} not found", status_code=404)

        # Create run
        run = await self.ingestion_repo.create_run(source=source_code, status="running")

        errors: list[dict] = []
        models_found = 0
        models_created = 0
        models_updated = 0
        models_skipped = 0

        try:
            parser = get_parser(source.parser_class, base_url=source.base_url, rate_limit_rpm=source.rate_limit_rpm)
            # Fetch
            try:
                raw = await parser.fetch()
            except DomainError:
                # Rate limit or fetch failure → mark run failed
                raise
            except Exception as e:
                # Unexpected fetch error → mark failed
                await self.ingestion_repo.finish_run(run.id, status="failed", errors=[{"model_slug": "_fetch", "error": str(e)}])
                await self.ingestion_repo.release_lock(source_code)
                # Re-raise as failed run? Return failed run
                updated = await self.ingestion_repo.get_run(run.id)
                return updated

            # Transform
            try:
                items: list[dict] = parser.transform(raw)
            except Exception as e:
                await self.ingestion_repo.finish_run(run.id, status="failed", errors=[{"model_slug": "_transform", "error": str(e)}])
                await self.ingestion_repo.release_lock(source_code)
                return await self.ingestion_repo.get_run(run.id)

            models_found = len(items)

            # Process in batches of BATCH_SIZE
            for batch_start in range(0, len(items), BATCH_SIZE):
                batch = items[batch_start : batch_start + BATCH_SIZE]
                for raw_item in batch:
                    slug = raw_item.get("slug") or ""
                    try:
                        # Validate basic required fields
                        display_name = raw_item.get("display_name")
                        if not display_name or not str(display_name).strip():
                            raise DomainError("display_name is required", status_code=422)
                        provider_slug = raw_item.get("provider_slug")
                        if not provider_slug:
                            raise DomainError("provider_slug is required", status_code=422)

                        # Resolve provider_id
                        provider = await self.provider_repo.get_by_slug(provider_slug)
                        if not provider:
                            # Auto-create provider for ingestion (minimal)
                            try:
                                provider = await self.provider_repo.create(slug=provider_slug, name=provider_slug.title())
                            except DomainError:
                                # If creation fails due to race, try fetch again
                                provider = await self.provider_repo.get_by_slug(provider_slug)
                                if not provider:
                                    raise

                        # Build upsert data for AIModel
                        data: dict[str, Any] = {
                            "provider_id": provider.id,
                            "slug": slug,
                            "display_name": str(display_name).strip(),
                            "family": raw_item.get("family"),
                            "version": raw_item.get("version"),
                            "modality": raw_item.get("modality") or ["text"],
                            "context_window": raw_item.get("context_window"),
                            "max_output_tokens": raw_item.get("max_output_tokens"),
                            "input_price_per_mtok": raw_item.get("input_price_per_mtok"),
                            "output_price_per_mtok": raw_item.get("output_price_per_mtok"),
                            "status": raw_item.get("status") or "draft",
                            "source": raw_item.get("source") or source_code,
                            "source_payload_hash": raw_item.get("source_payload_hash") or hashlib.sha256(json.dumps(raw_item, sort_keys=True, default=str).encode()).hexdigest(),
                            "source_url": raw_item.get("source_url"),
                        }
                        # Fix empty hash?
                        if not data["source_payload_hash"]:
                            data["source_payload_hash"] = hashlib.sha256(json.dumps(raw_item, sort_keys=True, default=str).encode()).hexdigest()

                        _, created = await self.model_repo.upsert(data)
                        if created:
                            models_created += 1
                        else:
                            models_updated += 1
                    except DomainError as e:
                        models_skipped += 1
                        errors.append({"model_slug": slug or raw_item.get("provider_slug") or "unknown", "error": str(e), "field": "validation"})
                    except Exception as e:
                        models_skipped += 1
                        errors.append({"model_slug": slug or "unknown", "error": str(e)})

            # Determine final status
            if models_found == 0:
                final_status = "success"
            elif errors:
                if models_created == 0 and models_updated == 0:
                    final_status = "failed"
                else:
                    final_status = "partial"
            else:
                final_status = "success"

            # Update run counts before finishing (to ensure models_found etc persisted even if finish fails)
            await self.ingestion_repo.update_run_counts(
                run.id,
                models_found=models_found,
                models_created=models_created,
                models_updated=models_updated,
                models_skipped=models_skipped,
                errors=errors if errors else None,
            )
            finished = await self.ingestion_repo.finish_run(run.id, status=final_status, errors=errors if errors else None)
            try:
                from app.taxonomy.services.public import clear_cache

                clear_cache()
            except Exception:
                pass
            return finished

        except DomainError:
            # If DomainError is 409 lock contention, don't finish run (no run created? Actually run created, need to mark failed)
            # But for lock case we already raised before creating run; here we have run, so mark failed if not already finished
            try:
                await self.ingestion_repo.finish_run(run.id, status="failed", errors=errors if errors else None)
            except Exception:
                pass
            raise
        except Exception as e:
            try:
                await self.ingestion_repo.update_run_counts(
                    run.id,
                    models_found=models_found,
                    models_created=models_created,
                    models_updated=models_updated,
                    models_skipped=models_skipped,
                )
                await self.ingestion_repo.finish_run(run.id, status="failed", errors=[{"model_slug": "_run", "error": str(e)}])
            except Exception:
                pass
            raise
        finally:
            try:
                await self.ingestion_repo.release_lock(source_code)
            except Exception:
                pass
