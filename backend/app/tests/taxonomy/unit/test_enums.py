"""Unit tests for taxonomy enums — RED phase (TDD).

Covers Task 1.1: Enum Definitions
Specs: spec-01,02,03,04,06,10
Design: Core Enums section
"""
import pytest
from pydantic import BaseModel


def test_provider_status_values():
    from app.taxonomy.models.enums import ProviderStatus

    assert ProviderStatus.ACTIVE == "active"
    assert ProviderStatus.DEPRECATED == "deprecated"
    assert ProviderStatus.BANNED == "banned"
    assert len(ProviderStatus) == 3
    # str subclass behavior
    assert isinstance(ProviderStatus.ACTIVE, str)


def test_model_status_values():
    from app.taxonomy.models.enums import ModelStatus

    assert ModelStatus.DRAFT == "draft"
    assert ModelStatus.PENDING_REVIEW == "pending_review"
    assert ModelStatus.APPROVED == "approved"
    assert ModelStatus.REJECTED == "rejected"
    assert ModelStatus.DEPRECATED == "deprecated"
    assert len(ModelStatus) == 5


def test_model_modality_values():
    from app.taxonomy.models.enums import ModelModality

    assert ModelModality.TEXT == "text"
    assert ModelModality.VISION == "vision"
    assert ModelModality.AUDIO == "audio"
    assert ModelModality.CODE == "code"
    assert ModelModality.EMBEDDING == "embedding"
    assert ModelModality.REASONING == "reasoning"
    assert len(ModelModality) == 6


def test_model_source_values():
    from app.taxonomy.models.enums import ModelSource

    assert ModelSource.OPENROUTER == "openrouter"
    assert ModelSource.HUGGINGFACE == "huggingface"
    assert ModelSource.LMSYS == "lmsys"
    assert ModelSource.MANUAL == "manual"
    assert len(ModelSource) == 4


def test_locale_values():
    from app.taxonomy.models.enums import Locale

    assert Locale.EN == "en"
    assert Locale.ES == "es"
    assert Locale.PT == "pt"
    assert Locale.FR == "fr"
    assert Locale.ZH == "zh"
    assert len(Locale) == 5


def test_webhook_event_values():
    from app.taxonomy.models.enums import WebhookEvent

    assert WebhookEvent.MODEL_APPROVED == "model.approved"
    assert WebhookEvent.MODEL_REJECTED == "model.rejected"
    assert WebhookEvent.MODEL_DEPRECATED == "model.deprecated"
    assert WebhookEvent.INGESTION_COMPLETED == "ingestion.completed"
    assert WebhookEvent.TAXONOMY_VERSION_ACTIVATED == "taxonomy.version_activated"
    assert len(WebhookEvent) == 5


def test_category_status_values():
    from app.taxonomy.models.enums import CategoryStatus

    assert CategoryStatus.ACTIVE == "active"
    assert CategoryStatus.DEPRECATED == "deprecated"
    assert len(CategoryStatus) == 2


def test_enum_str_serialization():
    from app.taxonomy.models.enums import ProviderStatus, ModelStatus, Locale

    # str() and value equality
    assert str(ProviderStatus.ACTIVE) == "active"
    assert ProviderStatus.ACTIVE.value == "active"
    # JSON serializable via value
    assert ProviderStatus.ACTIVE == "active"
    assert ModelStatus.DRAFT == "draft"
    assert Locale.ZH == "zh"


def test_pydantic_v2_serialization():
    from app.taxonomy.models.enums import ProviderStatus, ModelStatus, Locale, ModelModality

    class Dummy(BaseModel):
        provider_status: ProviderStatus
        model_status: ModelStatus
        locale: Locale
        modality: ModelModality

    obj = Dummy(
        provider_status=ProviderStatus.ACTIVE,
        model_status=ModelStatus.APPROVED,
        locale=Locale.ES,
        modality=ModelModality.CODE,
    )
    dumped = obj.model_dump()
    assert dumped["provider_status"] == "active"
    assert dumped["model_status"] == "approved"
    assert dumped["locale"] == "es"
    assert dumped["modality"] == "code"

    # round-trip via validation
    obj2 = Dummy.model_validate(
        {"provider_status": "banned", "model_status": "rejected", "locale": "zh", "modality": "reasoning"}
    )
    assert obj2.provider_status == ProviderStatus.BANNED
    assert obj2.locale == Locale.ZH


def test_enum_invalid_value():
    from app.taxonomy.models.enums import Locale

    with pytest.raises(ValueError):
        Locale("de")

    with pytest.raises(ValueError):
        Locale("xx")
