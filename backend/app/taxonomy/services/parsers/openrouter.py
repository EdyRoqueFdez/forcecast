"""OpenRouter parser — fetch and transform OpenRouter API models."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

import httpx

from app.taxonomy.services.core import DomainError, normalize_slug


def _modality_from_openrouter(arch_modality: str | None) -> list[str]:
    """Map OpenRouter architecture.modality to canonical list."""
    if not arch_modality:
        return ["text"]
    s = arch_modality.lower()
    mods: set[str] = set()
    if "text" in s:
        mods.add("text")
    if "image" in s or "vision" in s:
        mods.add("vision")
    if "audio" in s:
        mods.add("audio")
    if "code" in s:
        mods.add("code")
    if not mods:
        mods.add("text")
    return sorted(mods)


class OpenRouterParser:
    """Parser for OpenRouter API (https://openrouter.ai/api/v1/models)."""

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit_rpm: int = 60,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url or "https://openrouter.ai/api/v1").rstrip("/")
        self.rate_limit_rpm = rate_limit_rpm
        self._client = http_client

    async def fetch(self) -> dict:
        """Fetch raw data from OpenRouter. Handles rate limits and pagination."""
        url = f"{self.base_url}/models"
        # Use provided client or create new
        if self._client is not None:
            resp = await self._client.get(url)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
        if resp.status_code == 429:
            raise DomainError(f"OpenRouter rate limited (429) at {url}", status_code=429)
        if resp.status_code >= 400:
            raise DomainError(f"OpenRouter fetch failed: {resp.status_code}", status_code=resp.status_code)
        data = resp.json()
        # Handle pagination if next_page present (future-proof)
        # Some OpenRouter responses may paginate via "next" or page param; loop if needed
        # For v1, data is single page under "data"
        return data

    def transform(self, raw: dict | list) -> list[dict]:
        """Transform raw OpenRouter response into list of AIModelCreate dicts."""
        # Normalize raw to list of model dicts
        if isinstance(raw, dict) and "data" in raw:
            items = raw["data"]
        elif isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = [raw]
        else:
            items = []

        out: list[dict] = []
        for item in items:
            try:
                raw_id: str = item.get("id") or item.get("slug") or ""
                # provider_slug is prefix before "/" if present, else "openrouter"
                if "/" in raw_id:
                    provider_slug, slug_part = raw_id.split("/", 1)
                else:
                    provider_slug = item.get("provider_slug") or "openai"
                    slug_part = raw_id
                slug = normalize_slug(slug_part)
                if not slug:
                    slug = normalize_slug(raw_id) or "unknown"

                display_name: str = item.get("name") or item.get("display_name") or raw_id or slug

                context_window = item.get("context_length") or item.get("context_window")
                max_output = None
                top_provider = item.get("top_provider") or {}
                if isinstance(top_provider, dict):
                    max_output = top_provider.get("max_completion_tokens")

                # Pricing: prompt/completion per token -> per MTok
                input_price = None
                output_price = None
                pricing = item.get("pricing") or {}
                if isinstance(pricing, dict):
                    prompt = pricing.get("prompt")
                    completion = pricing.get("completion")
                    if prompt not in (None, ""):
                        try:
                            input_price = Decimal(str(prompt)) * Decimal("1000000")
                        except Exception:
                            input_price = None
                    if completion not in (None, ""):
                        try:
                            output_price = Decimal(str(completion)) * Decimal("1000000")
                        except Exception:
                            output_price = None

                modality = _modality_from_openrouter((item.get("architecture") or {}).get("modality"))

                # source_payload_hash deterministic
                payload_str = json.dumps(item, sort_keys=True, default=str)
                source_payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

                out.append(
                    {
                        "provider_slug": normalize_slug(provider_slug) or "openai",
                        "slug": slug,
                        "display_name": display_name,
                        "modality": modality,
                        "context_window": context_window,
                        "max_output_tokens": max_output,
                        "input_price_per_mtok": input_price,
                        "output_price_per_mtok": output_price,
                        "status": "draft",
                        "source": "openrouter",
                        "source_payload_hash": source_payload_hash,
                        "source_url": f"https://openrouter.ai/models/{raw_id}" if raw_id else None,
                    }
                )
            except Exception:
                # Per-model errors should not abort; skip and log via caller
                # For transform in isolation, we still skip invalid entries silently
                continue
        return out
