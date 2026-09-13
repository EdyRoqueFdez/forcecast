# Spec: HU-A07 — Base Reputation System

## Requirements

### REQ-01: Initial Reputation
**Priority**: MUST
**Description**: New users start with base reputation.

**Given** user registers
**When** account is created
**Then** reputation_score = 1.0

### REQ-02: Reputation Calculation
**Priority**: MUST
**Description**: Reputation calculated from multiple factors.

**Given** user has activity
**When** reputation is calculated
**Then** formula = tenure_score + votes_score + consistency_score - reports_penalty

### REQ-03: Tenure Score
**Priority**: SHOULD
**Description**: Older accounts have higher tenure score.

**Given** account age in days
**When** calculating tenure score
**Then** score = min(account_days / 365, 2.0)

### REQ-04: Votes Score
**Priority**: SHOULD
**Description**: Active voters earn votes score.

**Given** user has cast votes
**When** calculating votes score
**Then** score = min(votes_cast / 50, 2.0)

### REQ-05: Consistency Score
**Priority**: SHOULD
**Description**: Regular voting patterns earn consistency bonus.

**Given** user votes regularly
**When** calculating consistency score
**Then** score = 0.5 if votes in 7 of last 30 days

### REQ-06: Reports Penalty
**Priority**: MUST
**Description**: Reports reduce reputation.

**Given** user has reports
**When** calculating reputation
**Then** penalty = reports_received * 0.5

### REQ-07: Vote Weight
**Priority**: MUST
**Description**: Vote weight scales with reputation.

**Given** user casts vote
**When** calculating vote weight
**Then** weight = max(reputation_score * 1.0, 0.1)

### REQ-08: Bot Detection
**Priority**: SHOULD
**Description**: Low reputation triggers bot signals.

**Given** reputation_score < 0.5
**When** user attempts action
**Then** is_strict_mode returns True

### REQ-09: Profile Display
**Priority**: MUST
**Description**: Reputation visible in profile.

**Given** user views profile
**When** profile is loaded
**Then** reputation_score is included

## Non-Functional Requirements

### NFR-01: Performance
- Reputation calculation must be async
- Cache reputation for 1 hour

### NFR-02: Accuracy
- Reputation must be accurate to 2 decimal places
- Updates must be atomic

### NFR-03: Auditability
- All reputation changes must be logged
