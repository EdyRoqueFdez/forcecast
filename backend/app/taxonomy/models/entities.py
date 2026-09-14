"""Taxonomy SQLAlchemy entities — 14 models with constraints, FKs, indexes."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


# Helpers
def _uuid() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.now(UTC)

# Use JSON for sqlite compat, JSONB for postgres (migration will use JSONB)
JSONType = JSON().with_variant(JSONB(), "postgresql")

# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------
class Provider(Base):
    __tablename__ = "providers"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_providers_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_docs_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class ProviderTranslation(Base):
    __tablename__ = "provider_translations"
    __table_args__ = (
        UniqueConstraint("provider_id", "locale", name="uq_provider_translations_provider_locale"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# TaxonomyVersion — must be defined before Category due to FK
# ---------------------------------------------------------------------------
class TaxonomyVersion(Base):
    __tablename__ = "taxonomy_versions"
    __table_args__ = (
        UniqueConstraint("version", name="uq_taxonomy_versions_version"),
        Index(
            "uq_taxonomy_versions_is_current",
            "is_current",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ---------------------------------------------------------------------------
# AIModel + ModelTranslation
# ---------------------------------------------------------------------------
class AIModel(Base):
    __tablename__ = "ai_models"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_ai_models_slug"),
        UniqueConstraint("provider_id", "slug", name="uq_ai_models_provider_slug"),
        UniqueConstraint("provider_id", "family", "version", name="uq_ai_models_provider_family_version"),
        UniqueConstraint("source_payload_hash", name="uq_ai_models_source_payload_hash"),
        CheckConstraint("context_window IS NULL OR context_window > 0", name="ck_ai_models_context_window_positive"),
        CheckConstraint("max_output_tokens IS NULL OR max_output_tokens > 0", name="ck_ai_models_max_output_positive"),
        CheckConstraint("input_price_per_mtok IS NULL OR input_price_per_mtok >= 0", name="ck_ai_models_input_price_nonneg"),
        CheckConstraint("output_price_per_mtok IS NULL OR output_price_per_mtok >= 0", name="ck_ai_models_output_price_nonneg"),
        Index("idx_ai_model_provider_status", "provider_id", "status", postgresql_where=text("status = 'approved'"), sqlite_where=text("status = 'approved'")),
        Index("idx_ai_model_provider_id", "provider_id"),
        Index("idx_ai_model_status", "status"),
        # modality GIN placeholder — real GIN created in migration
        Index("idx_ai_model_modality_gin", "modality"),
        # search GIN placeholders — real GIN created in migration via tsvector
        Index("idx_ai_model_slug", "slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modality: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_price_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    output_price_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deprecation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    source_payload_hash: Mapped[str] = mapped_column(String(255), nullable=False, default="", unique=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class ModelTranslation(Base):
    __tablename__ = "model_translations"
    __table_args__ = (
        UniqueConstraint("model_id", "locale", name="uq_model_translations_model_locale"),
        Index("idx_ai_model_search_translations", "model_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# ModelHosting
# ---------------------------------------------------------------------------
class ModelHosting(Base):
    __tablename__ = "model_hostings"
    __table_args__ = (
        UniqueConstraint("model_id", "provider_id", name="uq_model_hostings_model_provider"),
        Index(
            "idx_model_hosting_model",
            "model_id",
            "is_primary",
            postgresql_where=text("is_primary = true"),
            sqlite_where=text("is_primary = 1"),
            unique=True,
        ),
        Index("idx_model_hosting_provider", "provider_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


# ---------------------------------------------------------------------------
# Category + CategoryTranslation
# ---------------------------------------------------------------------------
class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("slug", "taxonomy_version", name="uq_categories_slug_version"),
        Index("idx_categories_parent", "parent_id"),
        Index("idx_categories_taxonomy_version", "taxonomy_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True)
    taxonomy_version: Mapped[str] = mapped_column(String(50), ForeignKey("taxonomy_versions.version", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class CategoryTranslation(Base):
    __tablename__ = "category_translations"
    __table_args__ = (
        UniqueConstraint("category_id", "locale", name="uq_category_translations_category_locale"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# ModelCategory association
# ---------------------------------------------------------------------------
class ModelCategory(Base):
    __tablename__ = "model_categories"
    __table_args__ = (
        Index("idx_model_category_lookup", "category_id", "taxonomy_version"),
        Index("idx_model_category_model", "model_id"),
    )

    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id", ondelete="RESTRICT"), primary_key=True)
    taxonomy_version: Mapped[str] = mapped_column(String(50), ForeignKey("taxonomy_versions.version", ondelete="RESTRICT"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# Orchestrator + OrchestratorTranslation + OrchestratorProvider
# ---------------------------------------------------------------------------
class Orchestrator(Base):
    __tablename__ = "orchestrators"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_orchestrators_slug"),
        Index("idx_orchestrators_slug", "slug"),
        Index("idx_orchestrators_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    maintainer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    license: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    # Relationships
    translations: Mapped[list[OrchestratorTranslation]] = relationship(
        "OrchestratorTranslation", back_populates="orchestrator", cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrchestratorTranslation(Base):
    __tablename__ = "orchestrator_translations"
    __table_args__ = (
        UniqueConstraint("orchestrator_id", "locale", name="uq_orchestrator_translations_orchestrator_locale"),
        Index("idx_orchestrator_translations_orchestrator", "orchestrator_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    orchestrator_id: Mapped[str] = mapped_column(String(36), ForeignKey("orchestrators.id", ondelete="CASCADE"), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    orchestrator: Mapped[Orchestrator] = relationship("Orchestrator", back_populates="translations")


class OrchestratorProvider(Base):
    __tablename__ = "orchestrator_providers"
    __table_args__ = (
        UniqueConstraint("orchestrator_id", "provider_id", name="uq_orchestrator_providers_orchestrator_provider"),
    )

    orchestrator_id: Mapped[str] = mapped_column(String(36), ForeignKey("orchestrators.id", ondelete="CASCADE"), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("providers.id", ondelete="RESTRICT"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# OrchestratorCategory (HU-T11 — Filter orchestrators by category)
# ---------------------------------------------------------------------------
class OrchestratorCategory(Base):
    __tablename__ = "orchestrator_categories"
    __table_args__ = (
        UniqueConstraint("orchestrator_id", "category_id", name="uq_orchestrator_categories_orchestrator_category"),
    )

    orchestrator_id: Mapped[str] = mapped_column(String(36), ForeignKey("orchestrators.id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id", ondelete="RESTRICT"), primary_key=True)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ---------------------------------------------------------------------------
# Domain + DomainTranslation (HU-T05 — Problem Domains)
# ---------------------------------------------------------------------------
class Domain(Base):
    __tablename__ = "domains"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_domains_slug"),
        Index("idx_domains_slug", "slug"),
        Index("idx_domains_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("domains.id", ondelete="RESTRICT"), nullable=True)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class DomainTranslation(Base):
    __tablename__ = "domain_translations"
    __table_args__ = (
        UniqueConstraint("domain_id", "locale", name="uq_domain_translations_domain_locale"),
        Index("idx_domain_translations_domain", "domain_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    domain_id: Mapped[str] = mapped_column(String(36), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# IngestionSource + IngestionRun
# ---------------------------------------------------------------------------
class IngestionSource(Base):
    __tablename__ = "ingestion_sources"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parser_class: Mapped[str] = mapped_column(String(255), nullable=False)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    base_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        Index("idx_ingestion_run_source_status", "source", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(50), ForeignKey("ingestion_sources.code", ondelete="RESTRICT"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    models_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    models_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    models_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    models_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[list | None] = mapped_column(JSONType, nullable=True)


# ---------------------------------------------------------------------------
# WebhookRegistration + WebhookDelivery
# ---------------------------------------------------------------------------
class WebhookRegistration(Base):
    __tablename__ = "webhook_registrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    secret: Mapped[str] = mapped_column(String(500), nullable=False)
    events: Mapped[list] = mapped_column(JSONType, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint("delivery_id", name="uq_webhook_deliveries_delivery_id"),
        Index(
            "idx_webhook_delivery_pending",
            "status",
            "next_retry_at",
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    webhook_id: Mapped[str] = mapped_column(String(36), ForeignKey("webhook_registrations.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# LocaleMeta
# ---------------------------------------------------------------------------
class LocaleMeta(Base):
    __tablename__ = "locale_meta"

    locale: Mapped[str] = mapped_column(String(10), primary_key=True)
    native_name: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, default="ltr")
    plural_categories: Mapped[list] = mapped_column(JSONType, nullable=False)
    week_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
