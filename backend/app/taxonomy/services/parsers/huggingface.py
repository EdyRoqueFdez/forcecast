"""HuggingFace Hub parser."""

from __future__ import annotations

import hashlib
import json

import httpx

from app.taxonomy.services.core import DomainError, normalize_slug


def _modality_from_hf(tags: list, pipeline_tag: str | None) -> list[str]:
    tags_lower = [t.lower() for t in (tags or [])]
    pt = (pipeline_tag or "").lower()
    combined = " ".join(tags_lower) + " " + pt

    mods: set[str] = set()
    if any(k in combined for k in ["text-generation", "text2text", "conversational", "translation", "summarization"]):
        mods.add("text")
    if any(k in combined for k in ["text-to-image", "image-text", "vision", "visual", "image"]):
        mods.add("vision")
    if any(k in combined for k in ["audio", "speech", "whisper", "automatic-speech-recognition", "text-to-speech"]):
        mods.add("audio")
    if any(k in combined for k in ["code", "codellama"]):
        mods.add("code")
    if "embedding" in combined or "sentence-similarity" in combined:
        mods.add("embedding")
    if not mods:
        mods.add("text")
    return sorted(mods)


class HuggingFaceParser:
    """Parser for HuggingFace Hub API."""

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit_rpm: int = 30,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url or "https://huggingface.co/api").rstrip("/")
        self.rate_limit_rpm = rate_limit_rpm
        self._client = http_client

    async def fetch(self) -> list[dict]:
        url = f"{self.base_url}/models"
        if self._client is not None:
            resp = await self._client.get(url)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params={"limit": 100})
        if resp.status_code == 429:
            raise DomainError(f"HuggingFace rate limited (429) at {url}", status_code=429)
        if resp.status_code >= 400:
            raise DomainError(f"HuggingFace fetch failed: {resp.status_code}", status_code=resp.status_code)
        return resp.json()

    def transform(self, raw: list | dict) -> list[dict]:
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
                raw_id: str = item.get("id") or item.get("modelId") or ""
                if "/" in raw_id:
                    provider_slug, slug_part = raw_id.split("/", 1)
                else:
                    provider_slug = item.get("author") or "huggingface"
                    slug_part = raw_id
                slug = normalize_slug(slug_part)
                if not slug:
                    slug = normalize_slug(raw_id) or "unknown"

                display_name = raw_id or slug
                tags = item.get("tags") or []
                pipeline_tag = item.get("pipeline_tag") or item.get("pipelineTag")

                modality = _modality_from_hf(tags if isinstance(tags, list) else [], pipeline_tag)

                payload_str = json.dumps(item, sort_keys=True, default=str)
                source_payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

                out.append(
                    {
                        "provider_slug": normalize_slug(provider_slug) or "huggingface",
                        "slug": slug,
                        "display_name": display_name,
                        "modality": modality,
                        "context_window": None,
                        "max_output_tokens": None,
                        "input_price_per_mtok": None,
                        "output_price_per_mtok": None,
                        "status": "draft",
                        "source": "huggingface",
                        "source_payload_hash": source_payload_hash,
                        "source_url": f"https://huggingface.co/{raw_id}" if raw_id else None,
                    }
                )
            except Exception:
                continue
        return out
