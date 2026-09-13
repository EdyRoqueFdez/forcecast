# AIModel Specification

## Purpose

Define the AIModel entity — a specific versioned model offered by a provider. Models carry modality, pricing, context window, status lifecycle, and deduplication metadata. This is the core entity that all downstream domains (voting, recommendations) reference.

## Requirements

### Requirement: AIModel Entity

The system SHALL persist AIModel entities with fields: id (UUID PK), slug (str, globally unique, normalized), display_name (str, required), version (str, nullable), family (str, nullable), modality (list[enum]: text, vision, audio, code, embedding, reasoning), context_window (int, nullable, >0), max_output_tokens (int, nullable, >0), input_price_per_mtok (Decimal, nullable, ≥0, **reference only**), output_price_per_mtok (Decimal, nullable, ≥0, **reference only**), release_date (date, nullable), deprecation_date (date, nullable), status (enum: draft, pending_review, approved, rejected, deprecated), source (enum: openrouter, huggingface, lmsys, manual), source_url (URL, nullable), source_payload_hash (str, NOT NULL, default ''), created_at (auto), updated_at (auto).

#### Scenario: Create AIModel

- GIVEN a valid model payload with display_name "Claude 3.5 Sonnet" and provider_id referencing "anthropic"
- WHEN the admin creates the model
- THEN an AIModel row is persisted with status "draft"
- AND slug is normalized via R3

#### Scenario: Global Slug Uniqueness

- GIVEN an AIModel with slug "claude-3-5-sonnet" exists
- WHEN creating another AIModel with the same slug
- THEN the system returns 409 Conflict

### Requirement: AIModel Deduplication Constraints

The system SHALL enforce three DB-level unique constraints for deduplication: (provider_id, slug), (provider_id, family, version), and source_payload_hash (NOT NULL with default ''). On conflict, the system SHALL perform an upsert (INSERT ... ON CONFLICT DO UPDATE).

#### Scenario: Upsert on Slug Conflict

- GIVEN an AIModel with (provider_id=X, slug="gpt-4") exists
- WHEN ingestion inserts a model with the same (provider_id, slug) and a new source_payload_hash
- THEN the existing record is updated, not duplicated
- AND models_created count does not increase

#### Scenario: Upsert on Payload Hash

- GIVEN an AIModel with source_payload_hash="abc123" exists
- WHEN ingestion inserts a model with the same source_payload_hash but different slug
- THEN the existing record is updated via hash conflict

### Requirement: AIModel Status Transitions

The system SHALL enforce the following allowed transitions: draft→pending_review, pending_review→approved, pending_review→rejected, approved→deprecated. Any other transition SHALL be rejected with 409 Conflict. Only approved models appear in the public API.

#### Scenario: Valid Transition

- GIVEN an AIModel with status "pending_review"
- WHEN an admin approves the model
- THEN the status changes to "approved"

#### Scenario: Invalid Transition

- GIVEN an AIModel with status "draft"
- WHEN an admin attempts to approve the model directly
- THEN the system returns 409 Conflict
