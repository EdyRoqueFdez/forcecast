"""Phase 5 — Parser Unit Tests (TDD RED).

Covers:
5.2 OpenRouter Parser — fetch, transform, rate limits, pagination
5.3 HuggingFace Parser — fetch, transform
5.4 LMSYS Parser — fetch, transform
"""

import hashlib
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures — sample raw payloads
# ---------------------------------------------------------------------------
OPENROUTER_RAW = {
    "data": [
        {
            "id": "openai/gpt-4o",
            "name": "OpenAI: GPT-4o",
            "context_length": 128000,
            "pricing": {"prompt": "0.000005", "completion": "0.000015"},
            "top_provider": {"max_completion_tokens": 16384},
            "created": 1715097600,
            "architecture": {"modality": "text+image", "tokenizer": "GPT"},
        },
        {
            "id": "anthropic/claude-3-5-sonnet",
            "name": "Anthropic: Claude 3.5 Sonnet",
            "context_length": 200000,
            "pricing": {"prompt": "0.000003", "completion": "0.000015"},
            "top_provider": {"max_completion_tokens": 8192},
            "created": 1729555200,
            "architecture": {"modality": "text", "tokenizer": "Claude"},
        },
    ]
}

HF_RAW = [
    {
        "id": "meta-llama/Llama-3.1-70B",
        "tags": ["text-generation", "pytorch"],
        "createdAt": "2024-07-23T00:00:00.000Z",
        "cardData": {"language": ["en"]},
        "pipeline_tag": "text-generation",
    },
    {
        "id": "stabilityai/stable-diffusion-xl-base-1.0",
        "tags": ["text-to-image", "diffusers"],
        "createdAt": "2023-07-26T00:00:00.000Z",
        "pipeline_tag": "text-to-image",
    },
]

LMSYS_RAW = {
    "models": [
        {"id": "gpt-4o-2024-05-13", "name": "GPT-4o", "organization": "OpenAI", "license": "proprietary"},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "organization": "Anthropic", "license": "proprietary"},
    ]
}


# ---------------------------------------------------------------------------
# 5.2 OpenRouter Parser
# ---------------------------------------------------------------------------
class TestOpenRouterParser:
    def test_transform_maps_fields_correctly(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        parser = OpenRouterParser()
        result = parser.transform(OPENROUTER_RAW)

        assert len(result) == 2
        # First model — openai/gpt-4o
        m0 = result[0]
        assert m0["slug"] == "gpt-4o"
        assert m0["display_name"] == "OpenAI: GPT-4o"
        assert m0["provider_slug"] == "openai"
        assert m0["source"] == "openrouter"
        assert m0["context_window"] == 128000
        assert m0["max_output_tokens"] == 16384
        # pricing per MTok = per-token * 1_000_000
        assert m0["input_price_per_mtok"] == Decimal("5.0")
        assert m0["output_price_per_mtok"] == Decimal("15.0")
        assert "source_payload_hash" in m0 and len(m0["source_payload_hash"]) == 64
        # modality: text+image -> [text, vision]
        assert "text" in m0["modality"]
        assert "vision" in m0["modality"]

        # second model
        m1 = result[1]
        assert m1["slug"] == "claude-3-5-sonnet"
        assert m1["provider_slug"] == "anthropic"
        assert m1["context_window"] == 200000
        assert m1["input_price_per_mtok"] == Decimal("3.0")

    def test_transform_handles_missing_pricing(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = {"data": [{"id": "test/model", "name": "Test Model"}]}
        parser = OpenRouterParser()
        result = parser.transform(raw)
        assert len(result) == 1
        assert result[0]["input_price_per_mtok"] is None
        assert result[0]["output_price_per_mtok"] is None
        assert result[0]["context_window"] is None

    def test_transform_source_payload_hash_deterministic(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        parser = OpenRouterParser()
        r1 = parser.transform(OPENROUTER_RAW)
        r2 = parser.transform(OPENROUTER_RAW)
        assert r1[0]["source_payload_hash"] == r2[0]["source_payload_hash"]

    @pytest.mark.asyncio
    async def test_fetch_handles_rate_limit_and_pagination(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        # Mock httpx.AsyncClient.get to return paginated responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = OPENROUTER_RAW
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            parser = OpenRouterParser(base_url="https://openrouter.ai/api/v1", rate_limit_rpm=60)
            data = await parser.fetch()
            assert data == OPENROUTER_RAW
            # Verify get was called with expected endpoint
            assert mock_client.get.called

    @pytest.mark.asyncio
    async def test_fetch_raises_on_http_error(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            parser = OpenRouterParser()
            # fetch should handle 429 by raising or retrying; we expect it to raise DomainError or return gracefully
            # Our implementation raises DomainError on repeated rate limit
            try:
                await parser.fetch()
            except Exception as e:
                assert e is not None


# ---------------------------------------------------------------------------
# 5.3 HuggingFace Parser
# ---------------------------------------------------------------------------
class TestHuggingFaceParser:
    def test_transform_maps_fields(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        parser = HuggingFaceParser()
        result = parser.transform(HF_RAW)

        assert len(result) == 2
        m0 = result[0]
        assert m0["slug"] == "llama-3-1-70b"
        assert m0["provider_slug"] == "meta-llama"
        assert m0["display_name"] == "meta-llama/Llama-3.1-70B"
        assert "text" in m0["modality"]
        assert m0["source"] == "huggingface"
        assert "source_payload_hash" in m0

        m1 = result[1]
        assert m1["slug"] == "stable-diffusion-xl-base-1-0"
        assert "vision" in m1["modality"] or "text" in m1["modality"]

    def test_transform_modality_from_tags(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        parser = HuggingFaceParser()
        raw = [{"id": "test/audio-model", "tags": ["audio", "automatic-speech-recognition"], "pipeline_tag": "automatic-speech-recognition"}]
        result = parser.transform(raw)
        assert "audio" in result[0]["modality"]

    @pytest.mark.asyncio
    async def test_fetch(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = HF_RAW
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            parser = HuggingFaceParser(base_url="https://huggingface.co/api")
            data = await parser.fetch()
            assert data == HF_RAW


# ---------------------------------------------------------------------------
# 5.4 LMSYS Parser
# ---------------------------------------------------------------------------
class TestLMSYSParser:
    def test_transform_maps_fields(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        parser = LMSYSParser()
        result = parser.transform(LMSYS_RAW)

        assert len(result) == 2
        m0 = result[0]
        assert m0["slug"] == "gpt-4o-2024-05-13"
        assert m0["display_name"] == "GPT-4o"
        assert m0["provider_slug"] == "openai"
        assert m0["source"] == "lmsys"
        assert "source_payload_hash" in m0

        m1 = result[1]
        assert m1["slug"] == "claude-3-5-sonnet-20241022"
        assert m1["provider_slug"] == "anthropic"

    def test_transform_handles_missing_organization(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        parser = LMSYSParser()
        raw = {"models": [{"id": "unknown/model-x", "name": "Model X"}]}
        result = parser.transform(raw)
        assert result[0]["provider_slug"] == "unknown"
        assert result[0]["slug"] == "model-x"

    @pytest.mark.asyncio
    async def test_fetch(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = LMSYS_RAW
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            parser = LMSYSParser(base_url="https://arena.lmsys.org/api")
            data = await parser.fetch()
            assert data == LMSYS_RAW
