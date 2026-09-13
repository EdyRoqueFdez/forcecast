"""LMSYS Chatbot Arena parser."""

from __future__ import annotations

import hashlib
import json

import httpx

from app.taxonomy.services.core import DomainError, normalize_slug

# Known organization mapping to provider slug
_ORG_TO_PROVIDER = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
    "meta": "meta",
    "mistral": "mistral",
    "cohere": "cohere",
    "deepseek": "deepseek",
    "alibaba": "alibaba",
    "qwen": "qwen",
    "xai": "xai",
}


def _provider_from_org(org: str | None, model_id: str) -> str:
    if org:
        low = org.lower().strip()
        if low in _ORG_TO_PROVIDER:
            return _ORG_TO_PROVIDER[low]
        # try partial match
        for key, slug in _ORG_TO_PROVIDER.items():
            if key in low:
                return slug
        return normalize_slug(low) or "unknown"
    # fallback: infer from model id prefix
    if "/" in model_id:
        return normalize_slug(model_id.split("/", maxsplit=1)[0]) or "unknown"
    # heuristic: gpt -> openai, claude -> anthropic
    low_id = model_id.lower()
    if "gpt" in low_id:
        return "openai"
    if "claude" in low_id:
        return "anthropic"
    if "gemini" in low_id:
        return "google"
    if "llama" in low_id:
        return "meta"
    return "unknown"


class LMSYSParser:
    """Parser for LMSYS Chatbot Arena API."""

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit_rpm: int = 20,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url or "https://arena.lmsys.org/api").rstrip("/")
        self.rate_limit_rpm = rate_limit_rpm
        self._client = http_client

    async def fetch(self) -> dict:
        url = f"{self.base_url}/models"
        if self._client is not None:
            resp = await self._client.get(url)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
        if resp.status_code == 429:
            raise DomainError(f"LMSYS rate limited (429) at {url}", status_code=429)
        if resp.status_code >= 400:
            raise DomainError(f"LMSYS fetch failed: {resp.status_code}", status_code=resp.status_code)
        return resp.json()

    def transform(self, raw: dict | list) -> list[dict]:
        # LMSYS raw is {"models": [...]} or list
        if isinstance(raw, dict) and "models" in raw:
            items = raw["models"]
        elif isinstance(raw, dict) and "data" in raw:
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
                raw_id: str = item.get("id") or item.get("model_id") or ""
                display_name: str = item.get("name") or item.get("display_name") or raw_id
                org = item.get("organization") or item.get("org") or item.get("provider")

                # LMSYS ids are global, slug is last part after "/" normalized
                if "/" in raw_id:
                    slug_part = raw_id.split("/", 1)[1]
                    slug = normalize_slug(slug_part)
                else:
                    slug = normalize_slug(raw_id)
                if not slug:
                    slug = normalize_slug(display_name) or "unknown"

                provider_slug = _provider_from_org(org, raw_id)

                payload_str = json.dumps(item, sort_keys=True, default=str)
                source_payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

                out.append(
                    {
                        "provider_slug": provider_slug,
                        "slug": slug,
                        "display_name": display_name,
                        "modality": ["text"],
                        "context_window": None,
                        "max_output_tokens": None,
                        "input_price_per_mtok": None,
                        "output_price_per_mtok": None,
                        "status": "draft",
                        "source": "lmsys",
                        "source_payload_hash": source_payload_hash,
                        "source_url": f"https://arena.lmsys.org/models/{raw_id}" if raw_id else None,
                    }
                )
            except Exception:
                continue
        return out
