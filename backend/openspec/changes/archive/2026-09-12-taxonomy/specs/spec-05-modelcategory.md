# ModelCategory Specification

## Purpose

Define the ModelCategory association table — links AIModels to Categories within a specific TaxonomyVersion. This enables version-aware category assignments so historical votes reference the taxonomy active at creation time.

## Requirements

### Requirement: ModelCategory Association

The system SHALL persist ModelCategory associations with fields: model_id (FK → AIModel, ON DELETE CASCADE), category_id (FK → Category, ON DELETE RESTRICT), taxonomy_version (FK → TaxonomyVersion.version, ON DELETE RESTRICT), created_at (auto). Primary key: (model_id, category_id, taxonomy_version).

#### Scenario: Assign Model to Category

- GIVEN an AIModel "claude-3-5-sonnet" and Category "coding" in taxonomy_version="v1"
- WHEN assigning the model to the category
- THEN a ModelCategory row is persisted with taxonomy_version="v1"

#### Scenario: Duplicate Assignment Rejected

- GIVEN a ModelCategory for (model_id=X, category_id=Y, taxonomy_version="v1") exists
- WHEN attempting the same assignment again
- THEN the system returns 409 Conflict

### Requirement: ModelCategory FK Constraints

The system SHALL enforce ON DELETE CASCADE from AIModel (removing a model removes its category assignments) and ON DELETE RESTRICT from Category and TaxonomyVersion (cannot delete a category or version that has model associations).

#### Scenario: Model Deletion Cascades

- GIVEN a ModelCategory association for model_id=X
- WHEN the AIModel X is deleted
- THEN the ModelCategory row is cascade-deleted

#### Scenario: Category Deletion Blocked

- GIVEN a ModelCategory association for category_id=Y
- WHEN attempting to delete Category Y
- THEN the system returns 409 Conflict (ON DELETE RESTRICT)

### Requirement: ModelCategory Indexes

The system SHALL create indexes: (category_id, taxonomy_version) for category-scoped lookups, and (model_id) for model-scoped lookups. These support the public API's category filter and model detail endpoints.

#### Scenario: Category Lookup Performance

- GIVEN 10,000 ModelCategory rows across 17 categories
- WHEN querying models by category_slug="coding" in taxonomy_version="v1"
- THEN the query uses the (category_id, taxonomy_version) index
- AND returns results in <50ms
