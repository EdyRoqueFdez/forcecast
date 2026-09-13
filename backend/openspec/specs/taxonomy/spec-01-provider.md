# Provider Specification

## Purpose

Define the Provider entity — the canonical catalog of AI model publishers. Every AIModel references exactly one Provider. Providers carry metadata (website, docs, logo) and a status lifecycle.

## Requirements

### Requirement: Provider Entity

The system SHALL persist Provider entities with fields: id (UUID PK), slug (str, globally unique, normalized), name (str, required), website (URL, nullable), api_docs_url (URL, nullable), logo_url (URL, nullable), status (enum: active, deprecated, banned), created_at (auto), updated_at (auto).

#### Scenario: Create Provider

- GIVEN a valid provider payload with name "Anthropic" and slug "anthropic"
- WHEN the admin creates the provider
- THEN a Provider row is persisted with status "active"
- AND slug is normalized via R3 (slug normalization algorithm)

#### Scenario: Slug Uniqueness

- GIVEN a Provider with slug "openai" already exists
- WHEN creating another Provider with slug "openai"
- THEN the system returns 409 Conflict

### Requirement: Provider Status Lifecycle

The system SHALL support Provider statuses: active, deprecated, banned. Only active providers appear in public API responses.

#### Scenario: Deprecate Provider

- GIVEN a Provider with status "active"
- WHEN an admin sets status to "deprecated"
- THEN the Provider status updates to "deprecated"
- AND associated AIModels remain unchanged (no cascade status change)

#### Scenario: Public API Excludes Deprecated

- GIVEN a Provider with status "deprecated"
- WHEN a public client requests the providers list
- THEN the deprecated Provider is excluded from results

### Requirement: Provider Translations

The system SHALL support translations for Provider via ProviderTranslation entity: id (UUID PK), provider_id (FK → Provider, ON DELETE CASCADE), locale (enum: en, es, pt, fr, zh), name (str, required), description (text, nullable). Unique constraint: (provider_id, locale).

#### Scenario: Create Provider Translation

- GIVEN a Provider "anthropic" exists
- WHEN creating a ProviderTranslation with locale "es" and name "Anthropic"
- THEN the translation is persisted

#### Scenario: Duplicate Locale Rejected

- GIVEN a ProviderTranslation for (provider_id, locale="es") exists
- WHEN creating another ProviderTranslation for the same provider and locale
- THEN the system returns 409 Conflict