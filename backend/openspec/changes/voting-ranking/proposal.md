# Proposal: Voting HUs Ranking & Implementation Plan

## Context
All 12 Voting HUs have been partially or fully implemented. This proposal ranks the remaining work by difficulty and priority to guide the next implementation phase.

## Current Status
- **V01-V07**: Fully implemented (cast vote, change vote, view votes, rankings)
- **V08**: Partial (admin role check missing, reputation adjustment not integrated)
- **V09**: Partial (only burst detection, missing 3 algorithms)
- **V10**: Partial (endpoint exists but has field name bug, no CSV/JSON export)
- **V11**: Partial (wrong imports, missing privacy fields)
- **V12**: Partial (ReputationService exists, not integrated into VoteService)

## Ranking by Difficulty (Easiest → Hardest)

### 1. V10 — Vote History (BUG FIX)
**Difficulty: Easy** | **Priority: Critical**
- Fix field name mismatch (event_type → action)
- Add CSV/JSON export endpoint
- **Why first**: Runtime crash in production

### 2. V03 — Comment Edit
**Difficulty: Easy** | **Priority: High**
- Add PATCH /votes/{vote_id}/comment endpoint
- ~50 lines of code
- **Why**: Quick win, comment field already exists

### 3. V12 — Reputation-Weighted Voting
**Difficulty: Medium-High** | **Priority: High (foundational)**
- Integrate ReputationService into VoteService
- Add batch recalculation job
- **Why**: Unlocks weighted rankings, differentiator for Forcecast

### 4. V08 — Admin Role Check + Reputation Adjustment
**Difficulty: Medium-High** | **Priority: Medium (security)**
- Add admin role verification
- Wire ReputationService for report confirmation
- Add duplicate report detection
- **Why**: Security vulnerability without admin check

### 5. V11 — Public Votes with Privacy
**Difficulty: Medium** | **Priority: Medium**
- Fix wrong imports and model references
- Add User.profile_visibility field + migration
- Add proper data filtering
- **Why**: Privacy is important but less critical than security

### 6. V09 — Anomaly Detection (4 Algorithms)
**Difficulty: Hard** | **Priority: Low (data-dependent)**
- 90% same-target detection
- Device fingerprint correlation
- <1 minute vote change detection
- Weight reduction/exclusion
- **Why**: Requires real vote data, defense-in-depth feature

## Recommended Implementation Order

```
Phase 1 — Quick Wins (close gaps)
├── V10: Fix field name bug + add export
└── V03: Add comment edit endpoint

Phase 2 — Foundation (unlocks weighted rankings)
└── V12: Integrate ReputationService

Phase 3 — Security & Privacy
├── V08: Admin role check + reputation adjustment
└── V11: Privacy fields + proper imports

Phase 4 — Advanced Features
└── V09: Anomaly detection algorithms
```

## Key Insight
V01-V07 are done. The remaining work is about **closing bugs** (V10), **security hardening** (V08), **integration** (V12), and **advanced features** (V09). The highest-ROI move is V12 because it unlocks the entire weighted-ranking value proposition.

## Ready for Specs
Yes — this proposal provides clear ranking and implementation phases for the remaining voting HUs.
