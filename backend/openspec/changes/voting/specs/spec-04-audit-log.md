# Spec: AuditLog Model

- **Path:** `openspec/changes/voting/specs/spec-04-audit-log.md`
- **Version:** `1.0.0`
- **Status:** Draft
- **Owner:** Forcecast Core Team
- **Last Updated:** `2026-09-12`

## 1. Purpose

Define the append-only audit log that records all sensitive actions for compliance (RG-07). This is internal-only, accessible to admins.

## 2. Entity: AuditLog

### 2.1 Table Schema

```sql
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    actor_id VARCHAR(36) NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(36),
    details JSONB,
    request_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Append-only
CREATE RULE audit_logs_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE audit_logs_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;
```

### 2.2 Constraints

| Constraint | Type | Description |
|------------|------|-------------|
| `pk_audit_logs_id` | PRIMARY KEY | `id` |
| `fk_audit_logs_actor` | FOREIGN KEY | `actor_id` → `users.id` |

### 2.3 Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_audit_logs_actor` | `actor_id` | Actor's audit trail |
| `idx_audit_logs_entity` | `entity_type, entity_id` | Entity audit trail |
| `idx_audit_logs_action` | `action` | Action type queries |
| `idx_audit_logs_created` | `created_at` | Time-range queries |

### 2.4 Rules

- **RG-07:** AuditLog MUST be append-only. No UPDATE or DELETE operations.
- **RG-07:** Every sensitive action MUST be logged: login, vote, change, revoke, approval, taxonomy change, revocation.
- **RG-02:** AuditLog MUST be internal-only, accessible to admins.

## 3. Actions to Log

| Action | Entity Type | Details |
|--------|------------|---------|
| `user.login` | `user` | `{provider, method}` |
| `user.logout` | `user` | `{}` |
| `vote.cast` | `vote` | `{target_type, target_id, category_id}` |
| `vote.change` | `vote` | `{target_type, old_target_id, new_target_id, category_id}` |
| `vote.revoke` | `vote` | `{target_type, target_id, category_id}` |
| `model.approve` | `model` | `{model_id, old_status, new_status}` |
| `model.reject` | `model` | `{model_id, old_status, new_status}` |
| `model.deprecate` | `model` | `{model_id, old_status, new_status}` |
| `taxonomy.activate` | `taxonomy_version` | `{version_id, old_version, new_version}` |
| `api_key.create` | `api_key` | `{key_id, name, scopes}` |
| `api_key.revoke` | `api_key` | `{key_id, name}` |

## 4. Scenarios

### 4.1 Log Vote Action

**Given** a user casts a vote
**When** the vote is committed
**Then** an AuditLog MUST be created with `action='vote.cast'`
**And** `actor_id` MUST be the voting user's ID
**And** `details` MUST include `target_type`, `target_id`, `category_id`

### 4.2 Admin Access Only

**Given** an admin queries the audit log
**When** the request is authenticated with admin role
**Then** the audit logs MUST be returned

### 4.3 Non-Admin Access Denied

**Given** a non-admin user queries the audit log
**When** the request is authenticated with user role
**Then** the API MUST return `403 Forbidden`

## 5. Non-Functional Requirements

- **Append-only:** No UPDATE or DELETE operations at DB level
- **Performance:** Log creation MUST complete in < 50ms (p95)
- **Retention:** 5 years per compliance (RG-17)

## Artifact
- **Path:** `openspec/changes/voting/specs/spec-04-audit-log.md`
- **Next:** `spec-05-vote-api.md`
