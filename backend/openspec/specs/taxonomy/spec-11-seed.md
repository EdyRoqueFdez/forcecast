# Seed Data Specification

## Purpose

Define the seed data requirements — the initial dataset that bootstraps the taxonomy. Seed data includes providers, models, categories, translations in 5 locales, ingestion sources, and model hostings. The seed command must be idempotent and validate translation completeness. **model_hostings.json contains NO price fields.**

## Requirements

### Requirement: Seed Data Completeness

The system SHALL provide seed data files under seeds/ containing: providers.json (≥10 providers), models.json (≥30 models across providers with reference prices), model_hostings.json (≥30 rows, 1 per model for v1, **no price fields**), categories.json (17 categories with parent tree), translations for all 5 locales (en, es, pt, fr, zh) for ALL entities (Provider, Category, AIModel), ingestion_sources.json (3 sources: openrouter, huggingface, lmsys).

#### Scenario: Provider Seed Count

- GIVEN seeds/providers.json is loaded
- WHEN counting providers
- THEN there are at least 10 unique providers

#### Scenario: Model Seed Count

- GIVEN seeds/models.json is loaded
- WHEN counting models
- THEN there are at least 30 unique models across multiple providers

#### Scenario: Category Seed Count

- GIVEN seeds/categories.json is loaded
- WHEN counting categories
- THEN there are exactly 17 categories matching the canonical tree in spec §6

### Requirement: Translation Coverage

The system SHALL require translations in all 5 locales (en, es, pt, fr, zh) for every seed entity (Provider, Category, AIModel). The seed command SHALL fail if any entity is missing translations for any locale.

#### Scenario: Complete Translations

- GIVEN all seed entities have translations in 5 locales
- WHEN running the seed command
- THEN the command completes successfully

#### Scenario: Missing Translation Fails

- GIVEN a Provider in seeds without a Portuguese translation
- WHEN running the seed command
- THEN the command fails with an error listing the missing translation

### Requirement: Idempotent Seed Command

The system SHALL support a seed command: python -m app.db.seed --file seeds/. Running the command twice SHALL produce no duplicates. The command uses upsert semantics.

#### Scenario: Seed Twice No Duplicates

- GIVEN the seed command ran successfully once (10 providers, 30 models)
- WHEN running the seed command again
- THEN provider count remains 10 and model count remains 30

### Requirement: Ingestion Source Seeds

The system SHALL seed exactly 3 IngestionSource entries: openrouter, huggingface, lmsys. Each entry includes code, name, parser_class, rate_limit_rpm, and base_url.

#### Scenario: Source Seeds Present

- GIVEN seeds/ingestion_sources.json is loaded
- WHEN querying IngestionSource
- THEN 3 sources exist with correct codes and parser_class values

### Requirement: Model Hosting Seeds

The system SHALL seed ModelHosting rows for every seeded model (1 per model for v1), linking each model to its primary provider with is_primary=true. **model_hostings.json MUST NOT contain any price fields (input_price_override, output_price_override, etc.).**

#### Scenario: Hosting Per Model

- GIVEN 30 models are seeded
- WHEN counting ModelHosting rows
- THEN there are 30 rows, each with is_primary=true
- AND each hosting links a model to its correct provider

#### Scenario: No Price Fields in Hosting Seed

- GIVEN seeds/model_hostings.json is loaded
- WHEN inspecting the JSON structure
- THEN each row contains only: model_id, provider_id, endpoint_url, status, is_primary, created_at, updated_at
- AND no price-related fields exist (input_price_override, output_price_override, price, cost, etc.)