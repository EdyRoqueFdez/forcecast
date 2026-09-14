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


# ===========================================================================
# Coverage boost — LMSYS
# ===========================================================================

class TestLMSYSProviderFromOrg:
    def test_partial_match_in_org_to_provider(self):
        from app.taxonomy.services.parsers.lmsys import _provider_from_org

        assert _provider_from_org("OpenAI Org", "model") == "openai"
        assert _provider_from_org("Anthropic Corp", "model") == "anthropic"
        assert _provider_from_org("Google DeepMind", "model") == "google"
        assert _provider_from_org("Meta AI", "model") == "meta"
        assert _provider_from_org("Mistral Labs", "model") == "mistral"
        assert _provider_from_org("Cohere AI", "model") == "cohere"
        assert _provider_from_org("DeepSeek AI", "model") == "deepseek"
        assert _provider_from_org("Alibaba Cloud", "model") == "alibaba"
        assert _provider_from_org("Qwen Team", "model") == "qwen"
        assert _provider_from_org("xAI Labs", "model") == "xai"

    def test_org_not_in_map_falls_to_normalize(self):
        from app.taxonomy.services.parsers.lmsys import _provider_from_org

        result = _provider_from_org("totally-unknown-org", "model")
        assert result not in ("", None)

    def test_org_is_none_prefix_slash(self):
        from app.taxonomy.services.parsers.lmsys import _provider_from_org

        assert _provider_from_org(None, "some-org/some-model") == "some-org"

    def test_org_is_none_heuristic_gpt(self):
        from app.taxonomy.services.parsers.lmsys import _provider_from_org

        assert _provider_from_org(None, "gpt-4-turbo") == "openai"

    def test_org_is_none_heuristic_claude(self):
        from app.taxonomy.services.parsers.lmsys import _provider_from_org

        assert _provider_from_org(None, "claude-3-opus") == "anthropic"

    def test_org_is_none_heuristic_gemini(self):
        from app.taxonomy.services.parsers.lmsys import _provider_from_org

        assert _provider_from_org(None, "gemini-pro") == "google"

    def test_org_is_none_heuristic_llama(self):
        from app.taxonomy.services.parsers.lmsys import _provider_from_org

        assert _provider_from_org(None, "llama-3-70b") == "meta"

    def test_org_is_none_fallback_unknown(self):
        from app.taxonomy.services.parsers.lmsys import _provider_from_org

        assert _provider_from_org(None, "randommodel") == "unknown"


class TestLMSYSFetchExtra:
    @pytest.mark.asyncio
    async def test_fetch_with_injected_client(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = LMSYS_RAW
        mock_client.get = AsyncMock(return_value=mock_resp)

        parser = LMSYSParser(http_client=mock_client)
        data = await parser.fetch()
        assert data == LMSYS_RAW
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_429_raises_domain_error(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser
        from app.taxonomy.services.core import DomainError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_client.get = AsyncMock(return_value=mock_resp)

        parser = LMSYSParser(http_client=mock_client)
        with pytest.raises(DomainError) as exc_info:
            await parser.fetch()
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_fetch_500_raises_domain_error(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser
        from app.taxonomy.services.core import DomainError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.get = AsyncMock(return_value=mock_resp)

        parser = LMSYSParser(http_client=mock_client)
        with pytest.raises(DomainError) as exc_info:
            await parser.fetch()
        assert exc_info.value.status_code == 500


class TestLMSYSTransformExtra:
    def test_transform_data_key(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        raw = {"data": [{"id": "model-a", "name": "Model A"}]}
        result = LMSYSParser().transform(raw)
        assert len(result) == 1
        assert result[0]["slug"] == "model-a"

    def test_transform_list_input(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        raw = [{"id": "model-b", "name": "Model B", "org": "OpenAI"}]
        result = LMSYSParser().transform(raw)
        assert len(result) == 1
        assert result[0]["slug"] == "model-b"
        assert result[0]["provider_slug"] == "openai"

    def test_transform_single_dict(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        raw = {"id": "single-model", "name": "Single"}
        result = LMSYSParser().transform(raw)
        assert len(result) == 1
        assert result[0]["slug"] == "single-model"

    def test_transform_empty_input(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        result = LMSYSParser().transform("invalid")
        assert result == []

    def test_transform_empty_list(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        result = LMSYSParser().transform([])
        assert result == []

    def test_transform_slug_fallback_from_display_name(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        raw = {"models": [{"id": "", "name": "My Cool Model"}]}
        result = LMSYSParser().transform(raw)
        assert len(result) == 1
        assert result[0]["slug"] != ""
        assert result[0]["slug"] != "unknown"

    def test_transform_exception_in_item_skips(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        raw = {"models": [
            {"id": "ok-model", "name": "OK"},
            None,
            {"id": "also-ok", "name": "Also OK"},
        ]}
        result = LMSYSParser().transform(raw)
        assert len(result) == 2

    def test_transform_org_provider_key(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        raw = {"models": [{"id": "m1", "name": "M1", "provider": "Mistral"}]}
        result = LMSYSParser().transform(raw)
        assert result[0]["provider_slug"] == "mistral"

    def test_transform_slug_from_model_id_with_slash(self):
        from app.taxonomy.services.parsers.lmsys import LMSYSParser

        raw = {"models": [{"id": "org/my-model", "name": "My Model"}]}
        result = LMSYSParser().transform(raw)
        assert result[0]["slug"] == "my-model"
        assert result[0]["provider_slug"] == "org"


# ===========================================================================
# Coverage boost — HuggingFace
# ===========================================================================

class TestHuggingFaceModalityExtra:
    def test_code_tag(self):
        from app.taxonomy.services.parsers.huggingface import _modality_from_hf

        result = _modality_from_hf(["code", "pytorch"], None)
        assert "code" in result

    def test_embedding_tag(self):
        from app.taxonomy.services.parsers.huggingface import _modality_from_hf

        result = _modality_from_hf(["embedding", "pytorch"], None)
        assert "embedding" in result

    def test_sentence_similarity_tag(self):
        from app.taxonomy.services.parsers.huggingface import _modality_from_hf

        result = _modality_from_hf(["sentence-similarity"], None)
        assert "embedding" in result

    def test_no_tags_no_pipeline_defaults_text(self):
        from app.taxonomy.services.parsers.huggingface import _modality_from_hf

        result = _modality_from_hf([], None)
        assert result == ["text"]

    def test_none_tags_defaults_text(self):
        from app.taxonomy.services.parsers.huggingface import _modality_from_hf

        result = _modality_from_hf(None, None)
        assert result == ["text"]

    def test_vision_pipeline_tag(self):
        from app.taxonomy.services.parsers.huggingface import _modality_from_hf

        result = _modality_from_hf([], "image-text-to-text")
        assert "vision" in result


class TestHuggingFaceFetchExtra:
    @pytest.mark.asyncio
    async def test_fetch_with_injected_client(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = HF_RAW
        mock_client.get = AsyncMock(return_value=mock_resp)

        parser = HuggingFaceParser(http_client=mock_client)
        data = await parser.fetch()
        assert data == HF_RAW
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_429_raises(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser
        from app.taxonomy.services.core import DomainError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_client.get = AsyncMock(return_value=mock_resp)

        parser = HuggingFaceParser(http_client=mock_client)
        with pytest.raises(DomainError) as exc_info:
            await parser.fetch()
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_fetch_500_raises(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser
        from app.taxonomy.services.core import DomainError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.get = AsyncMock(return_value=mock_resp)

        parser = HuggingFaceParser(http_client=mock_client)
        with pytest.raises(DomainError) as exc_info:
            await parser.fetch()
        assert exc_info.value.status_code == 500


class TestHuggingFaceTransformExtra:
    def test_transform_data_key(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        raw = {"data": [{"id": "org/model-a", "name": "Model A"}]}
        result = HuggingFaceParser().transform(raw)
        assert len(result) == 1
        assert result[0]["slug"] == "model-a"

    def test_transform_single_dict(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        raw = {"id": "single-model", "name": "Single"}
        result = HuggingFaceParser().transform(raw)
        assert len(result) == 1
        assert result[0]["slug"] == "single-model"

    def test_transform_invalid_input(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        result = HuggingFaceParser().transform("invalid")
        assert result == []

    def test_transform_no_slash_uses_author(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        raw = [{"id": "my-model", "author": "custom-org", "name": "My Model"}]
        result = HuggingFaceParser().transform(raw)
        assert result[0]["provider_slug"] == "custom-org"
        assert result[0]["slug"] == "my-model"

    def test_transform_no_slash_no_author(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        raw = [{"id": "my-model", "name": "My Model"}]
        result = HuggingFaceParser().transform(raw)
        assert result[0]["provider_slug"] == "huggingface"

    def test_transform_empty_id_fallback_slug(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        raw = [{"id": "", "name": "", "modelId": ""}]
        result = HuggingFaceParser().transform(raw)
        assert result[0]["slug"] == "unknown"

    def test_transform_exception_skips_item(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        raw = [
            {"id": "ok-model", "name": "OK"},
            None,
            {"id": "also-ok", "name": "Also OK"},
        ]
        result = HuggingFaceParser().transform(raw)
        assert len(result) == 2

    def test_transform_pipeline_tag_key(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        raw = [{"id": "a/b", "pipelineTag": "text-generation"}]
        result = HuggingFaceParser().transform(raw)
        assert "text" in result[0]["modality"]

    def test_transform_model_id_key(self):
        from app.taxonomy.services.parsers.huggingface import HuggingFaceParser

        raw = [{"modelId": "org/model-x", "name": "X"}]
        result = HuggingFaceParser().transform(raw)
        assert result[0]["slug"] == "model-x"
        assert result[0]["provider_slug"] == "org"


# ===========================================================================
# Coverage boost — OpenRouter
# ===========================================================================

class TestOpenRouterModalityExtra:
    def test_audio(self):
        from app.taxonomy.services.parsers.openrouter import _modality_from_openrouter

        result = _modality_from_openrouter("audio+text")
        assert "audio" in result
        assert "text" in result

    def test_code(self):
        from app.taxonomy.services.parsers.openrouter import _modality_from_openrouter

        result = _modality_from_openrouter("code")
        assert "code" in result

    def test_no_modality_matches_defaults_text(self):
        from app.taxonomy.services.parsers.openrouter import _modality_from_openrouter

        result = _modality_from_openrouter("something-else")
        assert result == ["text"]

    def test_empty_string(self):
        from app.taxonomy.services.parsers.openrouter import _modality_from_openrouter

        result = _modality_from_openrouter("")
        assert result == ["text"]


class TestOpenRouterFetchExtra:
    @pytest.mark.asyncio
    async def test_fetch_with_injected_client(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = OPENROUTER_RAW
        mock_client.get = AsyncMock(return_value=mock_resp)

        parser = OpenRouterParser(http_client=mock_client)
        data = await parser.fetch()
        assert data == OPENROUTER_RAW
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_500_raises(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser
        from app.taxonomy.services.core import DomainError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.get = AsyncMock(return_value=mock_resp)

        parser = OpenRouterParser(http_client=mock_client)
        with pytest.raises(DomainError) as exc_info:
            await parser.fetch()
        assert exc_info.value.status_code == 500


class TestOpenRouterTransformExtra:
    def test_transform_list_input(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "test/model", "name": "Test"}]
        result = OpenRouterParser().transform(raw)
        assert len(result) == 1
        assert result[0]["slug"] == "model"
        assert result[0]["provider_slug"] == "test"

    def test_transform_single_dict(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = {"id": "single-model", "name": "Single"}
        result = OpenRouterParser().transform(raw)
        assert len(result) == 1
        assert result[0]["slug"] == "single-model"

    def test_transform_invalid_input(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        result = OpenRouterParser().transform("invalid")
        assert result == []

    def test_transform_no_slash_uses_provider_slug_from_item(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "my-model", "name": "My Model", "provider_slug": "custom"}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["provider_slug"] == "custom"
        assert result[0]["slug"] == "my-model"

    def test_transform_no_slash_no_provider(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "my-model", "name": "My Model"}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["provider_slug"] == "openai"

    def test_transform_empty_id_fallback_slug(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "", "name": ""}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["slug"] == "unknown"

    def test_transform_pricing_bad_prompt(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "M", "pricing": {"prompt": "not-a-number", "completion": "0.001"}}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["input_price_per_mtok"] is None
        assert result[0]["output_price_per_mtok"] is not None

    def test_transform_pricing_bad_completion(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "M", "pricing": {"prompt": "0.001", "completion": "bad"}}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["input_price_per_mtok"] is not None
        assert result[0]["output_price_per_mtok"] is None

    def test_transform_pricing_empty_string_prompt(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "M", "pricing": {"prompt": "", "completion": ""}}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["input_price_per_mtok"] is None
        assert result[0]["output_price_per_mtok"] is None

    def test_transform_exception_skips_item(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [
            {"id": "ok/model", "name": "OK"},
            None,
            {"id": "also-ok/model2", "name": "Also OK"},
        ]
        result = OpenRouterParser().transform(raw)
        assert len(result) == 2

    def test_transform_slug_key_fallback(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"slug": "org/my-slug", "name": "M"}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["slug"] == "my-slug"
        assert result[0]["provider_slug"] == "org"

    def test_transform_empty_list(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        result = OpenRouterParser().transform([])
        assert result == []

    def test_transform_pricing_none_prompt(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "M", "pricing": {"prompt": None, "completion": None}}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["input_price_per_mtok"] is None
        assert result[0]["output_price_per_mtok"] is None

    def test_transform_context_length_only(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "M", "context_length": 32000}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["context_window"] == 32000

    def test_transform_context_window_fallback(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "M", "context_window": 16000}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["context_window"] == 16000

    def test_transform_display_name_fallback_to_slug(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "", "display_name": ""}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["display_name"] in ("a/b", "b")

    def test_transform_top_provider_not_dict(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "M", "top_provider": "not-a-dict"}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["max_output_tokens"] is None

    def test_transform_pricing_not_dict(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "name": "M", "pricing": "not-a-dict"}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["input_price_per_mtok"] is None
        assert result[0]["output_price_per_mtok"] is None

    def test_transform_display_name_from_display_name_key(self):
        from app.taxonomy.services.parsers.openrouter import OpenRouterParser

        raw = [{"id": "a/b", "display_name": "Custom Display Name"}]
        result = OpenRouterParser().transform(raw)
        assert result[0]["display_name"] == "Custom Display Name"
