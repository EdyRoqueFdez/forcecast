"""Taxonomy initial schema — 14 tables, 8 indexes, 3 triggers.

Revision ID: 002_taxonomy_initial
Revises: 001_initial_auth
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_taxonomy_initial"
down_revision: Union[str, None] = "001_initial_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # taxonomy_versions — must be created first for FK
    op.create_table(
        "taxonomy_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("version", name="uq_taxonomy_versions_version"),
    )
    op.create_index(
        "uq_taxonomy_versions_is_current",
        "taxonomy_versions",
        ["is_current"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
        sqlite_where=sa.text("is_current = 1"),
    )

    # locale_meta
    op.create_table(
        "locale_meta",
        sa.Column("locale", sa.String(length=10), primary_key=True),
        sa.Column("native_name", sa.String(length=100), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False, server_default="ltr"),
        sa.Column("plural_categories", sa.JSON(), nullable=False),
        sa.Column("week_start", sa.Integer(), nullable=True),
    )

    # providers
    op.create_table(
        "providers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("api_docs_url", sa.String(length=500), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_providers_slug"),
    )

    # provider_translations
    op.create_table(
        "provider_translations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider_id", sa.String(length=36), sa.ForeignKey("providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("provider_id", "locale", name="uq_provider_translations_provider_locale"),
    )

    # ingestion_sources
    op.create_table(
        "ingestion_sources",
        sa.Column("code", sa.String(length=50), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parser_class", sa.String(length=255), nullable=False),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("base_url", sa.String(length=1000), nullable=True),
    )

    # ai_models
    op.create_table(
        "ai_models",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider_id", sa.String(length=36), sa.ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("family", sa.String(length=100), nullable=True),
        sa.Column("modality", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("max_output_tokens", sa.Integer(), nullable=True),
        sa.Column("input_price_per_mtok", sa.Numeric(12, 6), nullable=True),
        sa.Column("output_price_per_mtok", sa.Numeric(12, 6), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("deprecation_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="manual"),
        sa.Column("source_payload_hash", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_ai_models_slug"),
        sa.UniqueConstraint("provider_id", "slug", name="uq_ai_models_provider_slug"),
        sa.UniqueConstraint("provider_id", "family", "version", name="uq_ai_models_provider_family_version"),
        sa.UniqueConstraint("source_payload_hash", name="uq_ai_models_source_payload_hash"),
        sa.CheckConstraint("context_window IS NULL OR context_window > 0", name="ck_ai_models_context_window_positive"),
        sa.CheckConstraint("max_output_tokens IS NULL OR max_output_tokens > 0", name="ck_ai_models_max_output_positive"),
        sa.CheckConstraint("input_price_per_mtok IS NULL OR input_price_per_mtok >= 0", name="ck_ai_models_input_price_nonneg"),
        sa.CheckConstraint("output_price_per_mtok IS NULL OR output_price_per_mtok >= 0", name="ck_ai_models_output_price_nonneg"),
    )
    # 8 required indexes — provider_status partial, modality GIN, search GIN, etc.
    op.create_index(
        "idx_ai_model_provider_status",
        "ai_models",
        ["provider_id", "status"],
        postgresql_where=sa.text("status = 'approved'"),
        sqlite_where=sa.text("status = 'approved'"),
    )
    # modality GIN — real GIN on PG, btree fallback on sqlite
    try:
        op.create_index("idx_ai_model_modality_gin", "ai_models", ["modality"], postgresql_using="gin")
    except Exception:
        op.create_index("idx_ai_model_modality_gin", "ai_models", ["modality"])
    # search GIN placeholders
    try:
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_ai_model_search ON ai_models USING gin (to_tsvector('english', slug || ' ' || display_name || ' ' || COALESCE(family, '')))"))
    except Exception:
        op.create_index("idx_ai_model_search", "ai_models", ["slug", "display_name"])
    op.create_index("idx_ai_model_provider_id", "ai_models", ["provider_id"])
    op.create_index("idx_ai_model_status", "ai_models", ["status"])
    op.create_index("idx_ai_model_slug", "ai_models", ["slug"])

    # model_translations
    op.create_table(
        "model_translations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("model_id", sa.String(length=36), sa.ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("model_id", "locale", name="uq_model_translations_model_locale"),
    )
    try:
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_ai_model_search_translations ON model_translations USING gin (to_tsvector('simple', display_name || ' ' || COALESCE(description, '')))"))
    except Exception:
        op.create_index("idx_ai_model_search_translations", "model_translations", ["model_id"])

    # model_hostings
    op.create_table(
        "model_hostings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("model_id", sa.String(length=36), sa.ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", sa.String(length=36), sa.ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("endpoint_url", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("model_id", "provider_id", name="uq_model_hostings_model_provider"),
    )
    op.create_index(
        "idx_model_hosting_model",
        "model_hostings",
        ["model_id", "is_primary"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
        sqlite_where=sa.text("is_primary = 1"),
    )
    op.create_index("idx_model_hosting_provider", "model_hostings", ["provider_id"])

    # categories
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=50), sa.ForeignKey("taxonomy_versions.version", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", "taxonomy_version", name="uq_categories_slug_version"),
    )
    op.create_index("idx_categories_parent", "categories", ["parent_id"])
    op.create_index("idx_categories_taxonomy_version", "categories", ["taxonomy_version"])

    # category_translations
    op.create_table(
        "category_translations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("category_id", sa.String(length=36), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("category_id", "locale", name="uq_category_translations_category_locale"),
    )

    # model_categories
    op.create_table(
        "model_categories",
        sa.Column("model_id", sa.String(length=36), sa.ForeignKey("ai_models.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category_id", sa.String(length=36), sa.ForeignKey("categories.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("taxonomy_version", sa.String(length=50), sa.ForeignKey("taxonomy_versions.version", ondelete="RESTRICT"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_model_category_lookup", "model_categories", ["category_id", "taxonomy_version"])
    op.create_index("idx_model_category_model", "model_categories", ["model_id"])

    # ingestion_runs
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source", sa.String(length=50), sa.ForeignKey("ingestion_sources.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="running"),
        sa.Column("models_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("models_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("models_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("models_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.JSON(), nullable=True),
    )
    op.create_index("idx_ingestion_run_source_status", "ingestion_runs", ["source", "status"])

    # webhook_registrations
    op.create_table(
        "webhook_registrations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("secret", sa.String(length=500), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # webhook_deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("webhook_id", sa.String(length=36), sa.ForeignKey("webhook_registrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("delivery_id", sa.String(length=255), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("delivery_id", name="uq_webhook_deliveries_delivery_id"),
    )
    op.create_index(
        "idx_webhook_delivery_pending",
        "webhook_deliveries",
        ["status", "next_retry_at"],
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )

    # -----------------------------------------------------------------------
    # 3 triggers for historical immutability (PostgreSQL only)
    # -----------------------------------------------------------------------
    # Attempt to create PG triggers — safe to ignore on sqlite
    try:
        op.execute(sa.text("""
            CREATE OR REPLACE FUNCTION prevent_historical_category_change() RETURNS trigger AS $$
            BEGIN
                IF OLD.taxonomy_version != (SELECT version FROM taxonomy_versions WHERE is_current = true LIMIT 1) THEN
                    RAISE EXCEPTION 'Cannot modify historical taxonomy version %', OLD.taxonomy_version;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        op.execute(sa.text("""
            CREATE TRIGGER prevent_historical_category_update
            BEFORE UPDATE ON categories
            FOR EACH ROW EXECUTE FUNCTION prevent_historical_category_change();
        """))
        op.execute(sa.text("""
            CREATE TRIGGER prevent_historical_category_delete
            BEFORE DELETE ON categories
            FOR EACH ROW EXECUTE FUNCTION prevent_historical_category_change();
        """))
        op.execute(sa.text("""
            CREATE OR REPLACE FUNCTION prevent_historical_category_translation_change() RETURNS trigger AS $$
            BEGIN
                DECLARE v_tax_version TEXT;
                SELECT taxonomy_version INTO v_tax_version FROM categories WHERE id = OLD.category_id;
                IF v_tax_version != (SELECT version FROM taxonomy_versions WHERE is_current = true LIMIT 1) THEN
                    RAISE EXCEPTION 'Cannot modify historical category translation for version %', v_tax_version;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        op.execute(sa.text("""
            CREATE TRIGGER prevent_historical_category_translation_change
            BEFORE UPDATE OR DELETE ON category_translations
            FOR EACH ROW EXECUTE FUNCTION prevent_historical_category_translation_change();
        """))
        op.execute(sa.text("""
            CREATE OR REPLACE FUNCTION prevent_historical_model_category_change() RETURNS trigger AS $$
            BEGIN
                IF OLD.taxonomy_version != (SELECT version FROM taxonomy_versions WHERE is_current = true LIMIT 1) THEN
                    RAISE EXCEPTION 'Cannot modify historical model_category for version %', OLD.taxonomy_version;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        op.execute(sa.text("""
            CREATE TRIGGER prevent_historical_model_category_change
            BEFORE UPDATE OR DELETE ON model_categories
            FOR EACH ROW EXECUTE FUNCTION prevent_historical_model_category_change();
        """))
    except Exception:
        # sqlite: triggers as raw SQL with RAISE need separate syntax — create simple sqlite triggers
        try:
            op.execute(sa.text("""
                CREATE TRIGGER IF NOT EXISTS prevent_historical_category_update
                BEFORE UPDATE ON categories
                FOR EACH ROW
                WHEN OLD.taxonomy_version != (SELECT version FROM taxonomy_versions WHERE is_current = 1 LIMIT 1)
                BEGIN SELECT RAISE(ABORT, 'Cannot modify historical taxonomy version'); END;
            """))
            op.execute(sa.text("""
                CREATE TRIGGER IF NOT EXISTS prevent_historical_category_translation_change
                BEFORE UPDATE ON category_translations
                FOR EACH ROW
                WHEN (SELECT taxonomy_version FROM categories WHERE id = OLD.category_id) != (SELECT version FROM taxonomy_versions WHERE is_current = 1 LIMIT 1)
                BEGIN SELECT RAISE(ABORT, 'Cannot modify historical category translation'); END;
            """))
            op.execute(sa.text("""
                CREATE TRIGGER IF NOT EXISTS prevent_historical_model_category_change
                BEFORE UPDATE ON model_categories
                FOR EACH ROW
                WHEN OLD.taxonomy_version != (SELECT version FROM taxonomy_versions WHERE is_current = 1 LIMIT 1)
                BEGIN SELECT RAISE(ABORT, 'Cannot modify historical model_category'); END;
            """))
        except Exception:
            pass


def downgrade() -> None:
    # drop triggers first
    try:
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_historical_category_update ON categories"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_historical_category_delete ON categories"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_historical_category_translation_change ON category_translations"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_historical_model_category_change ON model_categories"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_historical_category_change() CASCADE"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_historical_category_translation_change() CASCADE"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_historical_model_category_change() CASCADE"))
    except Exception:
        pass
    try:
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_historical_category_update"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_historical_category_translation_change"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_historical_model_category_change"))
    except Exception:
        pass

    op.drop_index("idx_webhook_delivery_pending", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_registrations")
    op.drop_index("idx_ingestion_run_source_status", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
    op.drop_index("idx_model_category_model", table_name="model_categories")
    op.drop_index("idx_model_category_lookup", table_name="model_categories")
    op.drop_table("model_categories")
    op.drop_table("category_translations")
    op.drop_index("idx_categories_taxonomy_version", table_name="categories")
    op.drop_index("idx_categories_parent", table_name="categories")
    op.drop_table("categories")
    op.drop_index("idx_model_hosting_provider", table_name="model_hostings")
    op.drop_index("idx_model_hosting_model", table_name="model_hostings")
    op.drop_table("model_hostings")
    op.drop_index("idx_ai_model_slug", table_name="ai_models")
    op.drop_index("idx_ai_model_status", table_name="ai_models")
    op.drop_index("idx_ai_model_provider_id", table_name="ai_models")
    # idx_ai_model_search may be gin index created via raw SQL
    try:
        op.execute(sa.text("DROP INDEX IF EXISTS idx_ai_model_search"))
    except Exception:
        pass
    try:
        op.execute(sa.text("DROP INDEX IF EXISTS idx_ai_model_search_translations"))
    except Exception:
        pass
    try:
        op.drop_index("idx_ai_model_modality_gin", table_name="ai_models")
    except Exception:
        pass
    try:
        op.drop_index("idx_ai_model_search_translations", table_name="model_translations")
    except Exception:
        pass
    op.drop_index("idx_ai_model_provider_status", table_name="ai_models")
    op.drop_table("model_translations")
    op.drop_table("ai_models")
    op.drop_table("ingestion_sources")
    op.drop_table("provider_translations")
    op.drop_table("providers")
    op.drop_table("locale_meta")
    op.drop_index("uq_taxonomy_versions_is_current", table_name="taxonomy_versions")
    op.drop_table("taxonomy_versions")
