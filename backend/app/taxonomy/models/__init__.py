"""Taxonomy models package."""

# Re-export entities for convenience — ensures Base metadata is populated when package imported
from app.taxonomy.models.entities import (  # noqa: F401
    AIModel,
    Category,
    CategoryTranslation,
    IngestionRun,
    IngestionSource,
    LocaleMeta,
    ModelCategory,
    ModelHosting,
    ModelTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
    WebhookDelivery,
    WebhookRegistration,
)
from app.taxonomy.models.enums import (
    CategoryStatus,
    Direction,
    IngestionStatus,
    Locale,
    ModelModality,
    ModelSource,
    ModelStatus,
    ProviderStatus,
    WebhookDeliveryStatus,
    WebhookEvent,
)

__all__ = [
    "ProviderStatus",
    "ModelStatus",
    "ModelModality",
    "ModelSource",
    "Locale",
    "WebhookEvent",
    "CategoryStatus",
    "Direction",
    "IngestionStatus",
    "WebhookDeliveryStatus",
    # entities
    "Provider",
    "ProviderTranslation",
    "AIModel",
    "ModelTranslation",
    "ModelHosting",
    "Category",
    "CategoryTranslation",
    "ModelCategory",
    "TaxonomyVersion",
    "IngestionSource",
    "IngestionRun",
    "WebhookRegistration",
    "WebhookDelivery",
    "LocaleMeta",
]
