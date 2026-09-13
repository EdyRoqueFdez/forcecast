# Spec: Voting HUs Ranking Implementation

## Overview
This spec defines the implementation plan for the remaining 6 voting HUs, ranked by difficulty and priority.

## Requirements

### Phase 1 — Quick Wins

#### HU-V10: Vote History (BUG FIX)
**Given** a user is authenticated
**When** they call GET /api/v1/me/votes/history
**Then** the system should return their vote history with correct field names
**And** support filtering by category, target, event type
**And** support pagination
**And** support CSV/JSON export via Accept header

#### HU-V03: Comment Edit
**Given** a user has cast a vote with a comment
**When** they call PATCH /api/v1/votes/{vote_id}/comment
**Then** the system should update the comment
**And** create an audit log entry
**And** validate comment length (max 500 chars)

### Phase 2 — Foundation

#### HU-V12: Reputation-Weighted Voting
**Given** a user casts a vote
**When** the vote is processed
**Then** the system should calculate the user's reputation
**And** apply the reputation weight to the vote
**And** store the weight in VoteEvent.weight
**And** support batch recalculation via background job

### Phase 3 — Security & Privacy

#### HU-V08: Admin Role Check
**Given** an admin user reviews a report
**When** they approve/reject it
**Then** the system should verify admin role
**And** adjust the reported user's reputation
**And** recalculate affected rankings
**And** log the action to AuditLog

#### HU-V11: Public Votes with Privacy
**Given** a user views another user's votes
**When** the target profile is public
**Then** the system should return the votes
**And** filter out sensitive data (email, IP, device)
**And** respect privacy settings

### Phase 4 — Advanced Features

#### HU-V09: Anomaly Detection
**Given** votes are cast
**When** anomalous patterns are detected
**Then** the system should flag suspicious accounts
**And** reduce their vote weight to 0
**And** exclude them from rankings

## Technical Decisions
- Use existing ReputationService for V12
- Add admin role field to User model for V08
- Add profile_visibility field to User model for V11
- Create AnomalyDetectionService for V09

## Testing Strategy
- Unit tests for each service method
- Integration tests for API endpoints
- E2E tests for critical flows (vote casting with reputation)
- Performance tests for batch recalculation

## Ready for Design
Yes
