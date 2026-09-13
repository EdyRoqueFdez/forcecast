# TaxonomyVersion Specification

## Purpose

Define the TaxonomyVersion entity — an immutable snapshot of the category tree. Any change to the category tree (add, remove, rename, reparent) creates a new version. Only one version is is_current at any time. DB triggers enforce immutability of historical versions.

## Requirements

### Requirement: TaxonomyVersion Entity

The system SHALL persist TaxonomyVersion entities with fields: id (UUID PK), version (str, unique), released_at (datetime, required), notes (text, nullable), is_current (bool, partial unique index WHERE is_current=true).

#### Scenario: Create Version

- GIVEN no version "v2" exists
- WHEN an admin creates TaxonomyVersion with version="v2" and notes="Added agentic_workflows"
- THEN the version is persisted with is_current=false and released_at set

#### Scenario: Duplicate Version Rejected

- GIVEN a TaxonomyVersion with version="v1" exists
- WHEN creating another with version="v1"
- THEN the system returns 409 Conflict

### Requirement: Single Current Version

The system SHALL enforce exactly one TaxonomyVersion with is_current=true via a partial unique index. Activating a new version SHALL set the previous current version to is_current=false atomically.

#### Scenario: Activate Version

- GIVEN TaxonomyVersion "v1" is current and "v2" exists with is_current=false
- WHEN activating "v2"
- THEN "v2" becomes is_current=true
- AND "v1" becomes is_current=false
- AND the operation is atomic (no intermediate state with zero current versions)

#### Scenario: Activate Already Current

- GIVEN TaxonomyVersion "v1" is already current
- WHEN activating "v1" again
- THEN the operation succeeds idempotently (no error, no state change)

### Requirement: Historical Immutability

The system SHALL enforce immutability via PostgreSQL triggers: UPDATE and DELETE on Category, CategoryTranslation, and ModelCategory rows where taxonomy_version != current version SHALL be blocked. Only the current version's data is mutable.

#### Scenario: Block Historical Category Update

- GIVEN TaxonomyVersion "v1" is no longer current (is_current=false)
- WHEN attempting to UPDATE a Category with taxonomy_version="v1"
- THEN the trigger blocks the operation and the system returns 409 Conflict

#### Scenario: Allow Current Category Update

- GIVEN TaxonomyVersion "v1" is current (is_current=true)
- WHEN updating a Category with taxonomy_version="v1"
- THEN the update succeeds

### Requirement: Category Tree Versioning

The system SHALL create a new TaxonomyVersion when the category tree changes (add, remove, rename, reparent). The new version copies the current tree state. Old versions are read-only snapshots.

#### Scenario: New Category Triggers Version

- GIVEN TaxonomyVersion "v1" is current with 17 categories
- WHEN an admin adds a new category "agentic_workflows"
- THEN TaxonomyVersion "v2" is created automatically
- AND the new category belongs to "v2"
- AND "v1" categories remain unchanged
