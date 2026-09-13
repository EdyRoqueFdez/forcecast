# Design: HU-A07 — Base Reputation System

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Backend                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                Reputation Service                     │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  calculate_reputation(user_id)                 │  │   │
│  │  │  - tenure_score                                │  │   │
│  │  │  - votes_score                                 │  │   │
│  │  │  - consistency_score                           │  │   │
│  │  │  - reports_penalty                             │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐               │
│         │                 │                 │                │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐        │
│  │ Vote Service│  │   Profile   │  │ Anti-Bot    │        │
│  │ (weight)    │  │   (display) │  │ (detection) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Reputation Service

```python
# app/auth/services/reputation.py

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

class ReputationService:
    """Calculate and update user reputation."""
    
    BASE_REPUTATION = 1.0
    MAX_TENURE_SCORE = 2.0
    MAX_VOTES_SCORE = 2.0
    CONSISTENCY_BONUS = 0.5
    REPORT_PENALTY = 0.5
    MIN_REPUTATION = 0.1
    
    async def calculate_reputation(self, user: User, db: AsyncSession) -> float:
        """Calculate user's reputation score."""
        tenure = await self._tenure_score(user)
        votes = await self._votes_score(user, db)
        consistency = await self._consistency_score(user, db)
        reports = await self._reports_penalty(user, db)
        
        reputation = self.BASE_REPUTATION + tenure + votes + consistency - reports
        return max(reputation, self.MIN_REPUTATION)
    
    async def _tenure_score(self, user: User) -> float:
        """Score based on account age."""
        days = (datetime.now(timezone.utc) - user.created_at).days
        return min(days / 365, self.MAX_TENURE_SCORE)
    
    async def _votes_score(self, user: User, db: AsyncSession) -> float:
        """Score based on votes cast."""
        votes = await self._count_user_votes(user.id, db)
        return min(votes / 50, self.MAX_VOTES_SCORE)
    
    async def _consistency_score(self, user: User, db: AsyncSession) -> float:
        """Bonus for regular voting patterns."""
        active_days = await self._count_active_days(user.id, db, days=30)
        return self.CONSISTENCY_BONUS if active_days >= 7 else 0.0
    
    async def _reports_penalty(self, user: User, db: AsyncSession) -> float:
        """Penalty for reports received."""
        reports = await self._count_reports(user.id, db)
        return reports * self.REPORT_PENALTY
    
    def get_vote_weight(self, reputation: float) -> float:
        """Calculate vote weight from reputation."""
        return max(reputation, self.MIN_REPUTATION)
    
    def is_bot_like(self, reputation: float) -> bool:
        """Check if reputation indicates bot behavior."""
        return reputation < 0.5
```

### 2. Vote Weight Integration

```python
# Update vote_service.py

async def cast_vote(self, user: User, ...) -> dict:
    # Calculate vote weight based on reputation
    reputation_service = ReputationService()
    reputation = await reputation_service.calculate_reputation(user, self.session)
    weight = reputation_service.get_vote_weight(reputation)
    
    # Create vote event with weight
    event = await self.vote_event_repo.create({
        ...
        "weight": Decimal(str(weight)),
    })
```

### 3. Bot Detection Integration

```python
# Update anti_bot.py

def is_strict_mode(user: User) -> bool:
    """Check if user has bot-like signals."""
    if user.reputation_score < 0.5:
        return True
    # ... existing logic
```

### 4. Profile Display

```python
# Update profile.py

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user: User = Depends(get_current_user)):
    # Calculate fresh reputation
    reputation_service = ReputationService()
    reputation = await reputation_service.calculate_reputation(user, db)
    
    return ProfileResponse(
        ...
        reputation_score=round(reputation, 2),
    )
```

## Database Changes

### User Table (already exists)
- `reputation_score` field already exists (default 5.0)
- Need to change default to 1.0

## Configuration

### Environment Variables
```env
# Reputation
REPUTATION_BASE=1.0
REPUTATION_MAX_TENURE=2.0
REPUTATION_MAX_VOTES=2.0
REPUTATION_CONSISTENCY_BONUS=0.5
REPUTATION_REPORT_PENALTY=0.5
```

## Testing Strategy

### Unit Tests
- Test tenure score calculation
- Test votes score calculation
- Test consistency score calculation
- Test reports penalty calculation
- Test vote weight calculation
- Test bot detection

### Integration Tests
- Test reputation update on vote
- Test reputation in profile
- Test vote weight in voting

## Migration Plan

### Phase 1: Service (Day 1)
- Create ReputationService
- Add calculation methods

### Phase 2: Integration (Day 2)
- Update VoteService
- Update anti_bot

### Phase 3: Display (Day 3)
- Update profile endpoint
- Add tests
