# Category Specification

## Purpose

Define the Category entity — a task or capability area used to contextualize opinions and recommendations. Categories form a tree (max depth 2 in v1) and are versioned via TaxonomyVersion. Each category carries translations.

## Requirements

### Requirement: Category Entity

The system SHALL persist Category entities with fields: id (UUID PK), slug (str, unique per taxonomy_version), parent_id (FK → Category, nullable, ON DELETE RESTRICT), taxonomy_version (FK → TaxonomyVersion.version, ON DELETE RESTRICT), status (enum: active, deprecated), created_at (auto), updated_at (auto).

#### Scenario: Create Category

- GIVEN TaxonomyVersion "v1" exists and is_current=true
- WHEN creating a Category with slug "coding" and no parent
- THEN a Category row is persisted with taxonomy_version="v1" and status="active"

#### Scenario: Slug Unique Per Version

- GIVEN a Category with slug "coding" in taxonomy_version="v1" exists
- WHEN creating another Category with slug "coding" in taxonomy_version="v1"
- THEN the system returns 409 Conflict

#### Scenario: Same Slug in Different Version

- GIVEN a Category with slug "coding" in taxonomy_version="v1" exists
- WHEN creating a Category with slug "coding" in taxonomy_version="v2"
- THEN the creation succeeds (different taxonomy_version)

### Requirement: Category Tree Integrity

The system SHALL enforce tree integrity: parent_id references an existing Category in the same taxonomy_version. ON DELETE RESTRICT prevents deleting a parent that has children. Max depth is 2 in v1.

#### Scenario: Create Child Category

- GIVEN a Category "coding" exists in taxonomy_version="v1"
- WHEN creating a Category with slug "debugging" and parent_id pointing to "coding"
- THEN the child is persisted with correct parent reference

#### Scenario: Delete Parent with Children Rejected

- GIVEN a Category "coding" with child "debugging"
- WHEN attempting to delete "coding"
- THEN the system returns 409 Conflict (ON DELETE RESTRICT)

#### Scenario: Cycle Prevention

- GIVEN a Category "A" with parent_id pointing to "B"
- WHEN attempting to set "B"'s parent_id to "A"
- THEN the system rejects the update (would create cycle)

### Requirement: Category Translations

The system SHALL support translations for Category via CategoryTranslation entity: id (UUID PK), category_id (FK → Category, ON DELETE CASCADE), locale (enum: en, es, pt, fr, zh), name (str, required), description (text, nullable). Unique constraint: (category_id, locale).

#### Scenario: Create Category Translation

- GIVEN a Category "coding" exists
- WHEN creating a CategoryTranslation with locale="es" and name="Programación"
- THEN the translation is persisted

#### Scenario: Cascade Delete

- GIVEN a Category with translations in 5 locales
- WHEN the category is deleted
- THEN all associated CategoryTranslations are cascade-deleted
