# Design: Voting HUs Ranking Implementation

## Architecture Overview
The implementation follows the existing hexagonal architecture pattern with clear separation between API, service, and repository layers.

## Components

### 1. Vote History Fix (V10)
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Votes API      │────▶│   VoteService    │────▶│  VoteEvent Repo │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                                              │
        │                                              ▼
        │                                     ┌─────────────────┐
        │                                     │  VoteEvent Model │
        │                                     └─────────────────┘
        │
        ▼
┌─────────────────┐
│  Export Service  │
└─────────────────┘
```

**Changes:**
- Fix field mapping in VoteService.get_user_history()
- Add ExportService for CSV/JSON conversion
- Add Accept header parsing in API layer

### 2. Reputation Integration (V12)
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Votes API      │────▶│   VoteService    │────▶│ ReputationService│
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                      │                         │
        │                      ▼                         ▼
        │             ┌──────────────────┐     ┌─────────────────┐
        │             │  UserVote Model  │     │ Reputation Model│
        │             └──────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐
│  Batch Job      │
│  (APScheduler)  │
└─────────────────┘
```

**Changes:**
- Add ReputationService dependency to VoteService
- Calculate reputation at vote time
- Store weight in VoteEvent.weight
- Add background job for batch recalculation

### 3. Admin Role Check (V08)
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Admin API       │────▶│  ReportService   │────▶│ ReputationService│
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                      │                         │
        │                      ▼                         ▼
        │             ┌──────────────────┐     ┌─────────────────┐
        │             │   Report Model   │     │  User Model     │
        │             └──────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐
│  Auth Middleware │
│  (admin check)  │
└─────────────────┘
```

**Changes:**
- Add is_admin field to User model
- Create admin role verification middleware
- Wire ReportService to ReputationService
- Add AuditLog integration

### 4. Privacy Fields (V11)
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Public API      │────▶│  VoteService     │────▶│  User Model     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                      │                         │
        │                      ▼                         ▼
        │             ┌──────────────────┐     ┌─────────────────┐
        │             │  UserVote Model  │     │ Privacy Settings│
        │             └──────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐
│  Data Filter    │
│  (敏感数据过滤)  │
└─────────────────┘
```

**Changes:**
- Add profile_visibility field to User model
- Create privacy check middleware
- Add data filtering for sensitive fields

### 5. Anomaly Detection (V09)
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Ranking API     │────▶│ AnomalyDetection │────▶│  Redis          │
└─────────────────┘     │    Service       │     │  (sliding window)│
                        └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │  VoteEvent Repo  │
                        └──────────────────┘
```

**Changes:**
- Create AnomalyDetectionService with 4 algorithms
- Integrate with RankingService
- Add batch analysis job

## Database Changes

### Migration 009: User Roles & Privacy
```sql
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN profile_visibility VARCHAR(20) DEFAULT 'public';
```

### Migration 010: Report Reputation
```sql
ALTER TABLE reports ADD COLUMN reputation_adjustment DECIMAL(5,2);
```

## Security Considerations
- Admin role check must be middleware-level
- Reputation calculation must be server-side only
- Privacy filtering must happen at the data layer
- Anomaly detection must not expose user fingerprints

## Performance Considerations
- Batch recalculation should run during low-traffic hours
- Anomaly detection queries should use proper indexing
- Export should stream large datasets
- Cache invalidation for rankings after reputation changes

## Ready for Tasks
Yes
