"""Core enum definitions for Taxonomy domain.

Specs: spec-01..06,10
Design: Core Enums section
"""

from enum import Enum


class StrEnum(str, Enum):
    """Base for string enums with value-direct str() representation."""

    def __str__(self) -> str:
        return str(self.value)


class ProviderStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BANNED = "banned"


class ModelStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class ModelModality(StrEnum):
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    CODE = "code"
    EMBEDDING = "embedding"
    REASONING = "reasoning"


class ModelSource(StrEnum):
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"
    LMSYS = "lmsys"
    MANUAL = "manual"


class Locale(StrEnum):
    EN = "en"
    ES = "es"
    PT = "pt"
    FR = "fr"
    ZH = "zh"


class WebhookEvent(StrEnum):
    MODEL_APPROVED = "model.approved"
    MODEL_REJECTED = "model.rejected"
    MODEL_DEPRECATED = "model.deprecated"
    INGESTION_COMPLETED = "ingestion.completed"
    TAXONOMY_VERSION_ACTIVATED = "taxonomy.version_activated"


class CategoryStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class IngestionStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class WebhookDeliveryStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class Direction(StrEnum):
    LTR = "ltr"
    RTL = "rtl"
