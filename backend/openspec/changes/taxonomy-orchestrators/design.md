# Design: HU-T08 — List Orchestrators

## Architecture

### New Models (in entities.py)

```python
class Orchestrator(Base):
    __tablename__ = "orchestrators"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_orchestrators_slug"),
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


class OrchestratorTranslation(Base):
    __tablename__ = "orchestrator_translations"
    __table_args__ = (
        UniqueConstraint("orchestrator_id", "locale", name="uq_orchestrator_translations_orchestrator_locale"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    orchestrator_id: Mapped[str] = mapped_column(String(36), ForeignKey("orchestrators.id", ondelete="CASCADE"), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrchestratorProvider(Base):
    __tablename__ = "orchestrator_providers"
    __table_args__ = (
        UniqueConstraint("orchestrator_id", "provider_id", name="uq_orchestrator_providers_orchestrator_provider"),
    )

    orchestrator_id: Mapped[str] = mapped_column(String(36), ForeignKey("orchestrators.id", ondelete="CASCADE"), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("providers.id", ondelete="RESTRICT"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
```

### Service Layer (in public.py)

Add to `PublicService`:
- `list_orchestrators(locale, limit, cursor, sort, order, category)` - Query orchestrators with joins
- Reuse existing pagination and cache patterns

### API Layer (in public.py)

Add endpoint:
- `GET /api/v1/orchestrators` - List orchestrators with pagination, i18n, caching

### Repository Layer

New file: `app/taxonomy/repositories/orchestrator.py`
- `list_approved(limit, offset, sort, order)` - Query approved orchestrators
- `get_providers(orchestrator_ids)` - Batch fetch providers for orchestrators

## Database Schema

### Tables
1. `orchestrators` - Core orchestrator data
2. `orchestrator_translations` - Translated names/descriptions
3. `orchestrator_providers` - Many-to-many with providers

### Indexes
- `idx_orchestrators_slug` - Unique lookup by slug
- `idx_orchestrators_status` - Filter by status
- `idx_orchestrator_translations_orchestrator` - Join for translations

## Caching Strategy
- Cache key: `taxonomy:orchestrators:{hash(filters + locale + version)}`
- TTL: 60 seconds
- Invalidation: On admin updates (future)

## Performance Considerations
- Use `selectinload` for translations to avoid N+1
- Batch provider fetches per page
- Cursor-based pagination for large datasets
- p95 < 200ms target

## Migration Requirements
- Create 3 new tables
- Add indexes
- Seed example orchestrators

## Testing Strategy
- Unit tests for repository queries
- Integration tests for API endpoint
- Performance tests for p95 target

## Ready for Tasks
Yes
