# Admin API Specification

## Purpose

Define the admin write API — 7 endpoints for approval workflow, ingestion triggering, taxonomy version management, and webhook registration. Admin endpoints require authentication (JWT with role:admin or API key fk_admin_*) and enforce rate limiting.

## Requirements

### Requirement: Admin Authentication

The system SHALL require admin authentication on all /api/v1/admin/* endpoints via JWT with role:admin claim or API key prefix fk_admin_*. Unauthenticated requests return 401; non-admin role returns 403.

#### Scenario: JWT Auth Success

- GIVEN a valid JWT with role:admin
- WHEN calling any admin endpoint
- THEN the request is authenticated and processed

#### Scenario: Missing Auth

- GIVEN no Authorization header
- WHEN calling POST /api/v1/admin/ingestion/run
- THEN the system returns 401 with error.code="UNAUTHORIZED"

#### Scenario: Non-Admin Role

- GIVEN a valid JWT with role:user
- WHEN calling POST /api/v1/admin/models/{id}/approve
- THEN the system returns 403 with error.code="FORBIDDEN"

### Requirement: Trigger Ingestion

The system SHALL expose POST /api/v1/admin/ingestion/run with body {source: string}. Validates source exists in IngestionSource, starts async ingestion, returns IngestionRun. Emits ingestion.completed webhook on finish.

#### Scenario: Trigger OpenRouter Ingestion

- GIVEN IngestionSource "openrouter" exists
- WHEN admin sends POST /api/v1/admin/ingestion/run with {"source": "openrouter"}
- THEN an IngestionRun is created with status="running"
- AND the response includes the run id

#### Scenario: Invalid Source

- WHEN admin sends {"source": "nonexistent"}
- THEN the system returns 422 with error.code="VALIDATION_ERROR"

### Requirement: Approve Model

The system SHALL expose POST /api/v1/admin/models/{id}/approve. Validates model is in pending_review, has required fields (provider_id, slug, display_name, modality, at least one ModelHosting). Sets status to approved. Emits model.approved webhook.

#### Scenario: Approve Pending Model

- GIVEN a model in status "pending_review" with valid fields
- WHEN admin approves the model
- THEN status changes to "approved"
- AND model.approved webhook is emitted

#### Scenario: Approve Invalid Model

- GIVEN a model in status "pending_review" with no ModelHosting rows
- WHEN admin attempts approval
- THEN the system returns 422 with error indicating missing hosting

### Requirement: Reject Model

The system SHALL expose POST /api/v1/admin/models/{id}/reject with body {reason: string}. Sets status to rejected. Emits model.rejected webhook with reason in payload.

#### Scenario: Reject with Reason

- GIVEN a model in status "pending_review"
- WHEN admin rejects with reason "Duplicate of claude-3-5-sonnet"
- THEN status changes to "rejected"
- AND model.rejected webhook payload includes the reason

### Requirement: Create Taxonomy Version

The system SHALL expose POST /api/v1/admin/taxonomy/versions with body {version: string, notes?: string}. Creates a new TaxonomyVersion with is_current=false.

#### Scenario: Create Version

- WHEN admin creates version "v2" with notes
- THEN TaxonomyVersion "v2" is persisted with is_current=false

### Requirement: Activate Taxonomy Version

The system SHALL expose POST /api/v1/admin/taxonomy/versions/{id}/activate. Atomically sets the target version to is_current=true and all others to is_current=false. Emits taxonomy.version_activated webhook.

#### Scenario: Activate Version

- GIVEN TaxonomyVersion "v1" is current and "v2" exists
- WHEN admin activates "v2"
- THEN "v2" becomes current and "v1" is no longer current
- AND taxonomy.version_activated webhook is emitted

### Requirement: Register Webhook

The system SHALL expose POST /api/v1/admin/webhooks with body {url, events[], secret}. Creates a WebhookRegistration with is_active=true.

#### Scenario: Register Webhook

- WHEN admin registers webhook with url and events ["model.approved"]
- THEN WebhookRegistration is persisted with is_active=true

### Requirement: Admin Rate Limiting

The system SHALL enforce rate limits: anonymous 60/min, authenticated 300/min, admin 1000/min. Headers X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset on ALL responses. On 429: Retry-After header.

#### Scenario: Rate Limit Headers

- GIVEN an admin makes a request
- WHEN the response is returned
- THEN headers include X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

#### Scenario: 429 Response

- GIVEN an admin has exceeded 1000 requests/min
- WHEN making another request
- THEN the system returns 429 with Retry-After header
