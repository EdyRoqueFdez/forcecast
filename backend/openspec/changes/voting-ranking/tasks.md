# Tasks: Voting HUs Ranking Implementation

## Phase 1 — Quick Wins

### Task 1.1: Fix V10 Vote History Bug
**Priority:** Critical  
**Effort:** Small (1-2 hours)  
**Files:**
- `backend/app/voting/services/vote_service.py` — Fix field mapping
- `backend/app/voting/api/votes.py` — Update response schema
- `backend/tests/voting/test_history.py` — Add tests

**Steps:**
1. Read VoteEvent model to confirm field names
2. Fix field mapping in VoteService.get_user_history()
3. Update VoteHistoryItem schema
4. Add unit tests for field mapping
5. Run pytest to verify

### Task 1.2: Add V10 Export Functionality
**Priority:** High  
**Effort:** Medium (3-4 hours)  
**Files:**
- `backend/app/voting/services/export.py` — New ExportService
- `backend/app/voting/api/votes.py` — Add export endpoint
- `backend/tests/voting/test_export.py` — Add tests

**Steps:**
1. Create ExportService with CSV/JSON conversion
2. Add GET /api/v1/me/votes/history/export endpoint
3. Parse Accept header for format selection
4. Add streaming for large datasets
5. Add unit tests for export formats

### Task 1.3: Add V03 Comment Edit Endpoint
**Priority:** High  
**Effort:** Small (1-2 hours)  
**Files:**
- `backend/app/voting/api/votes.py` — Add PATCH endpoint
- `backend/app/voting/services/vote_service.py` — Add edit_comment method
- `backend/tests/voting/test_comment.py` — Add tests

**Steps:**
1. Add PATCH /api/v1/votes/{vote_id}/comment endpoint
2. Add VoteService.edit_comment() method
3. Validate comment length (max 500 chars)
4. Add AuditLog entry for comment edits
5. Add unit tests

## Phase 2 — Foundation

### Task 2.1: Integrate V12 Reputation Service
**Priority:** High  
**Effort:** Medium (4-6 hours)  
**Files:**
- `backend/app/voting/services/vote_service.py` — Add ReputationService dependency
- `backend/app/reputation/services/reputation.py` — Verify calculate_reputation
- `backend/tests/voting/test_reputation.py` — Add integration tests

**Steps:**
1. Add ReputationService as VoteService dependency
2. Calculate reputation at vote time
3. Apply weight to VoteEvent.weight
4. Add batch recalculation job
5. Add integration tests

### Task 2.2: Add V12 Batch Recalculation Job
**Priority:** Medium  
**Effort:** Medium (3-4 hours)  
**Files:**
- `backend/app/voting/services/batch.py` — New BatchRecalculationService
- `backend/app/core/scheduler.py` — Add APScheduler job
- `backend/tests/voting/test_batch.py` — Add tests

**Steps:**
1. Create BatchRecalculationService
2. Add APScheduler job for nightly recalculation
3. Add progress tracking
4. Add logging and monitoring
5. Add unit tests

## Phase 3 — Security & Privacy

### Task 3.1: Add V08 Admin Role Check
**Priority:** Medium (security)  
**Effort:** Medium (3-4 hours)  
**Files:**
- `backend/app/users/models/user.py` — Add is_admin field
- `backend/app/auth/middleware/admin.py` — New admin check middleware
- `backend/app/voting/api/admin.py` — Update admin endpoints
- `backend/tests/voting/test_admin.py` — Add tests

**Steps:**
1. Add is_admin field to User model
2. Create admin role verification middleware
3. Update admin endpoints to use middleware
4. Add unit tests for admin access

### Task 3.2: Add V08 Reputation Adjustment
**Priority:** Medium  
**Effort:** Medium (3-4 hours)  
**Files:**
- `backend/app/voting/services/report.py` — Add reputation adjustment
- `backend/app/reputation/services/reputation.py` — Add adjust_reputation method
- `backend/tests/voting/test_report_reputation.py` — Add tests

**Steps:**
1. Add adjust_reputation method to ReputationService
2. Wire ReportService to ReputationService
3. Add reputation adjustment on report confirmation
4. Add ranking cache invalidation
5. Add unit tests

### Task 3.3: Add V11 Privacy Fields
**Priority:** Medium  
**Effort:** Medium (3-4 hours)  
**Files:**
- `backend/app/users/models/user.py` — Add profile_visibility field
- `backend/app/db/migrations/versions/011_user_privacy.py` — New migration
- `backend/app/voting/api/votes.py` — Fix public votes endpoint
- `backend/tests/voting/test_privacy.py` — Add tests

**Steps:**
1. Add profile_visibility field to User model
2. Create migration 011
3. Fix public votes endpoint imports and fields
4. Add privacy check middleware
5. Add unit tests

## Phase 4 — Advanced Features

### Task 4.1: Add V09 90% Same-Target Detection
**Priority:** Low  
**Effort:** Large (6-8 hours)  
**Files:**
- `backend/app/voting/services/anomaly.py` — New AnomalyDetectionService
- `backend/app/voting/services/ranking.py` — Integrate anomaly detection
- `backend/tests/voting/test_anomaly.py` — Add tests

**Steps:**
1. Create AnomalyDetectionService
2. Add 90% same-target detection algorithm
3. Integrate with RankingService
4. Add batch analysis job
5. Add unit tests with synthetic data

### Task 4.2: Add V09 Device Fingerprint Correlation
**Priority:** Low  
**Effort:** Large (6-8 hours)  
**Files:**
- `backend/app/voting/services/anomaly.py` — Add fingerprint correlation
- `backend/app/voting/api/votes.py` — Collect device fingerprints
- `backend/tests/voting/test_fingerprint.py` — Add tests

**Steps:**
1. Add device fingerprint collection to vote endpoint
2. Add fingerprint correlation algorithm
3. Add multi-account detection
4. Add unit tests

### Task 4.3: Add V09 <1 Minute Vote Change Detection
**Priority:** Low  
**Effort:** Medium (4-6 hours)  
**Files:**
- `backend/app/voting/services/anomaly.py` — Add rapid change detection
- `backend/tests/voting/test_rapid_change.py` — Add tests

**Steps:**
1. Add timestamp analysis for vote changes
2. Add <1 minute detection algorithm
3. Add weight reduction for flagged users
4. Add unit tests

### Task 4.4: Add V09 Weight Reduction/Exclusion
**Priority:** Low  
**Effort:** Medium (3-4 hours)  
**Files:**
- `backend/app/voting/services/anomaly.py` — Add weight reduction
- `backend/app/voting/services/ranking.py` — Filter excluded users
- `backend/tests/voting/test_exclusion.py` — Add tests

**Steps:**
1. Add weight reduction algorithm
2. Add user exclusion from rankings
3. Add appeal process (future)
4. Add unit tests

## Dependencies
- Phase 1 has no dependencies
- Phase 2 depends on Phase 1 (V10 must be fixed first)
- Phase 3 depends on Phase 2 (reputation must be integrated)
- Phase 4 depends on Phase 3 (anomaly detection needs reputation data)

## Estimated Total Effort
- Phase 1: 5-8 hours
- Phase 2: 7-10 hours
- Phase 3: 9-12 hours
- Phase 4: 19-26 hours
- **Total: 40-56 hours**

## Ready for Implementation
Yes
