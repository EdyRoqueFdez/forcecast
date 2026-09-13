# Webhooks Specification

## Purpose

Define the webhook system — async HTTP callbacks for model lifecycle events. Webhooks are registered by admins, signed with HMAC-SHA256, delivered with idempotency keys, and retried with exponential backoff.

## Requirements

### Requirement: WebhookRegistration Entity

The system SHALL persist WebhookRegistration entities with fields: id (UUID PK), url (URL, required), secret (str, required, HMAC-SHA256), events (text[], required, subset of: model.approved, model.rejected, model.deprecated, ingestion.completed, taxonomy.version_activated), is_active (bool, default true), created_at (auto), updated_at (auto).

#### Scenario: Create Registration

- GIVEN admin provides url, events ["model.approved"], and secret
- WHEN registering a webhook
- THEN WebhookRegistration is persisted with is_active=true

#### Scenario: Invalid Events Rejected

- GIVEN admin provides events ["invalid.event"]
- WHEN registering a webhook
- THEN the system returns 422 with validation error listing valid events

### Requirement: WebhookDelivery Entity

The system SHALL persist WebhookDelivery entities with fields: id (UUID PK), webhook_id (FK → WebhookRegistration, ON DELETE CASCADE), event_type (str, required), payload (JSONB, required), delivery_id (str, unique, idempotency key), attempt (int, default 1), status (enum: pending, delivered, failed, dead_letter), response_status (int, nullable), response_body (text, nullable), error (text, nullable), created_at (auto), delivered_at (nullable), next_retry_at (nullable).

#### Scenario: Delivery Created

- GIVEN a model is approved and webhook registration for "model.approved" exists
- WHEN the approval event fires
- THEN a WebhookDelivery is created with status="pending" and unique delivery_id

### Requirement: Webhook Payload Envelope

The system SHALL send webhook payloads in envelope format: {id: uuid, type: event_type, timestamp: ISO8601, taxonomy_version: string, data: {...}}. Headers: X-Forcecast-Signature (HMAC-SHA256 of body), X-Forcecast-Delivery-Id (idempotency), X-Forcecast-Timestamp (replay protection).

#### Scenario: Signed Delivery

- GIVEN a webhook delivery for "model.approved"
- WHEN the HTTP request is sent
- THEN headers include X-Forcecast-Signature computed as HMAC-SHA256(secret, body)
- AND X-Forcecast-Delivery-Id matches the delivery_id
- AND X-Forcecast-Timestamp is within 5 minutes of current time

### Requirement: Retry Policy

The system SHALL retry failed deliveries with exponential backoff: 1m, 5m, 15m, 1h, 6h. Maximum 5 attempts. After 5 failures, status changes to dead_letter.

#### Scenario: Exponential Backoff

- GIVEN a delivery fails on attempt 1
- WHEN scheduling retry
- THEN next_retry_at is 1 minute later
- AND attempt increments to 2

#### Scenario: Dead Letter After Max Retries

- GIVEN a delivery has failed 5 times
- WHEN the 5th attempt fails
- THEN status changes to "dead_letter"
- AND no further retries are scheduled

### Requirement: Webhook Event Filtering

The system SHALL only deliver events matching the webhook's registered events array. A webhook registered for ["model.approved"] SHALL NOT receive "model.rejected" events.

#### Scenario: Event Matches

- GIVEN a webhook registered for events ["model.approved", "model.rejected"]
- WHEN a model is approved
- THEN a delivery is created for this webhook

#### Scenario: Event Does Not Match

- GIVEN a webhook registered for events ["model.approved"]
- WHEN a model is rejected
- THEN no delivery is created for this webhook
