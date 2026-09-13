# ModelHosting Specification

## Purpose

Define the ModelHosting entity — a deployment of a model on a specific provider. Enables multi-provider models (e.g., Llama hosted on Meta, Together, Groq). v1 enforces one primary hosting per model; schema is ready for v2 multi-hosting. **No pricing fields** — Forcecast is a comparison platform, not a marketplace.

## Requirements

### Requirement: ModelHosting Entity

The system SHALL persist ModelHosting entities with fields: id (UUID PK), model_id (FK → AIModel, ON DELETE CASCADE), provider_id (FK → Provider, ON DELETE RESTRICT), endpoint_url (URL, nullable), status (enum: active, deprecated), is_primary (bool, default false), created_at (auto), updated_at (auto). Unique constraint: (model_id, provider_id). **No price fields.**

#### Scenario: Create ModelHosting

- GIVEN an AIModel "claude-3-5-sonnet" and Provider "anthropic" exist
- WHEN creating a ModelHosting with model_id and provider_id
- THEN a ModelHosting row is persisted with is_primary=false and status="active"

#### Scenario: Duplicate Hosting Rejected

- GIVEN a ModelHosting for (model_id=X, provider_id=Y) exists
- WHEN creating another ModelHosting for the same pair
- THEN the system returns 409 Conflict

### Requirement: Primary Hosting Constraint

The system SHALL enforce exactly one is_primary=true per model_id via a partial unique index. ON DELETE CASCADE from AIModel ensures cleanup.

#### Scenario: Set Primary Hosting

- GIVEN a ModelHosting with is_primary=false for model_id=X
- WHEN setting is_primary=true
- THEN the hosting becomes the primary for that model

#### Scenario: Two Primaries Rejected

- GIVEN a ModelHosting with is_primary=true for model_id=X exists
- WHEN setting another hosting for the same model to is_primary=true
- THEN the system returns 409 Conflict

### Requirement: No Pricing Fields

The system SHALL NOT store any price fields on ModelHosting. Pricing is reference-only at AIModel level (input_price_per_mtok, output_price_per_mtok). ModelHosting only records deployment metadata.

#### Scenario: No Price Fields in ModelHosting

- GIVEN a ModelHosting row
- WHEN inspecting the row schema
- THEN there are no columns for input_price_override, output_price_override, or any other price field