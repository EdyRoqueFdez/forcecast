# Design: HU-A08 — CAPTCHA Turnstile Integration

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Registration │  │  First Vote  │  │ Burst Vote   │       │
│  │    Form      │  │    Button    │  │   Button     │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│         └─────────────────┼─────────────────┘                │
│                           │                                  │
│                    Turnstile Widget                           │
│                    (Cloudflare)                               │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   API Layer                           │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │  Register  │  │   Vote     │  │  Vote      │     │   │
│  │  │  Endpoint  │  │  Endpoint  │  │  Service   │     │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘     │   │
│  │        │               │               │              │   │
│  │        └───────────────┼───────────────┘              │   │
│  │                        │                              │   │
│  │              ┌─────────▼─────────┐                    │   │
│  │              │  TurnstileMiddleware│                    │   │
│  │              │  (Dependency)      │                    │   │
│  │              └─────────┬─────────┘                    │   │
│  │                        │                              │   │
│  │        ┌───────────────┼───────────────┐              │   │
│  │        │               │               │              │   │
│  │  ┌─────▼──────┐  ┌─────▼──────┐  ┌─────▼──────┐     │   │
│  │  │  Feature   │  │  Turnstile │  │  AuditLog  │     │   │
│  │  │   Flag     │  │  Service   │  │  Service   │     │   │
│  │  │ (PostHog)  │  │  (Cloud)   │  │            │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. TurnstileMiddleware (FastAPI Dependency)

```python
# app/auth/middleware/turnstile.py

class TurnstileConfig:
    enabled: bool = True
    secret_key: str
    site_key: str
    verify_url: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

class TurnstileMiddleware:
    def __init__(self, config: TurnstileConfig):
        self.config = config
    
    async def __call__(self, request: Request) -> str | None:
        # 1. Check feature flag
        if not self.config.enabled:
            return None
        
        # 2. Extract token from request
        token = await self._extract_token(request)
        if not token:
            raise HTTPException(403, "CAPTCHA token required")
        
        # 3. Verify with Cloudflare
        is_valid = await self._verify_token(token, request.client.host)
        if not is_valid:
            await self._log_failure(request)
            raise HTTPException(403, "CAPTCHA verification failed")
        
        return token
```

### 2. Burst Detection Service

```python
# app/voting/services/burst_detection.py

class BurstDetector:
    def __init__(self, redis: Any):
        self.redis = redis
    
    async def is_burst(self, user_id: str, window_seconds: int = 10) -> bool:
        """Check if user is voting in burst mode."""
        key = f"vote_burst:{user_id}"
        timestamps = await self._get_timestamps(key)
        
        # Clean old timestamps
        now = time.time()
        recent = [t for t in timestamps if now - t < window_seconds]
        
        # Burst if > 2 votes in window
        return len(recent) >= 2
    
    async def record_vote(self, user_id: str) -> None:
        """Record vote timestamp for burst detection."""
        key = f"vote_burst:{user_id}"
        await self._add_timestamp(key)
```

### 3. Feature Flag Integration

```python
# app/core/feature_flags.py

class FeatureFlags:
    def __init__(self, posthog_client=None):
        self.client = posthog_client
    
    async def is_enabled(self, flag_name: str, user_id: str | None = None) -> bool:
        """Check if feature flag is enabled."""
        if not self.client:
            return False
        
        return self.client.feature_enabled(
            flag_name,
            user_id or "anonymous",
            groups={"project": "forcecast"}
        )
```

### 4. AuditLog Integration

```python
# app/auth/services/audit_log.py

class AuditLogService:
    async def log_captcha_failure(
        self,
        user_id: str | None,
        ip_address: str,
        reason: str
    ) -> None:
        """Log failed CAPTCHA verification."""
        await self.create_entry(
            action="captcha_failed",
            user_id=user_id,
            ip_address=ip_address,
            details={"reason": reason}
        )
```

## Data Flow

### Registration Flow
```
1. User fills registration form
2. Turnstile widget generates token
3. Frontend sends: POST /auth/register {email, password, turnstile_token}
4. Backend:
   a. Check feature flag (captcha_turnstile_enabled)
   b. If enabled, verify turnstile_token
   c. If invalid, return 403
   d. If valid, create account
   e. Log success to AuditLog
```

### First Vote Flow
```
1. User clicks vote button
2. Frontend checks: is this first vote?
3. If first vote, show Turnstile widget
4. User completes Turnstile
5. Frontend sends: POST /voting/votes {event_id, model_slug, turnstile_token}
6. Backend:
   a. Check if user has voted before
   b. If first vote, verify turnstile_token
   c. If invalid, return 403
   d. If valid, record vote
   e. Log to AuditLog
```

### Burst Vote Flow
```
1. User votes rapidly
2. Frontend detects: votes within 10 seconds
3. Show Turnstile widget
4. User completes Turnstile
5. Frontend sends: POST /voting/votes {event_id, model_slug, turnstile_token}
6. Backend:
   a. Check burst detection
   b. If burst detected, verify turnstile_token
   c. If invalid, return 403
   d. If valid, record vote
   e. Log to AuditLog
```

## Database Changes

### AuditLog Table (already exists)
No schema changes needed. New action types:
- `captcha_failed`
- `captcha_success`
- `burst_detected`

## Configuration

### Environment Variables
```env
# Turnstile
TURNSTILE_SECRET_KEY=0x...
TURNSTILE_SITE_KEY=0x...

# Feature Flags (PostHog)
POSTHOG_API_KEY=phc_...
POSTHOG_HOST=https://app.posthog.com

# Feature Flag Names
FEATURE_CAPTCHA_REGISTRATION=captcha_registration_enabled
FEATURE_CAPTCHA_FIRST_VOTE=captcha_first_vote_enabled
FEATURE_CAPTCHA_BURST_VOTE=captcha_burst_vote_enabled
```

## Testing Strategy

### Unit Tests
- Mock Cloudflare API responses
- Test burst detection logic
- Test feature flag integration
- Test AuditLog creation

### Integration Tests
- Test complete registration flow
- Test complete voting flow
- Test failure scenarios

### Performance Tests
- Measure Turnstile latency
- Measure feature flag check latency
- Load test burst detection

## Rollout Plan

### Phase 1: Silent Mode (Week 1)
- Deploy with feature flags disabled
- Log all Turnstile verifications (success/failure)
- Monitor for false positives

### Phase 2: Registration Only (Week 2)
- Enable Turnstile for registration
- Monitor registration success rate
- Adjust thresholds if needed

### Phase 3: First Vote (Week 3)
- Enable Turnstile for first vote
- Monitor voting success rate
- Adjust thresholds if needed

### Phase 4: Burst Detection (Week 4)
- Enable Turnstile for burst votes
- Monitor burst detection accuracy
- Adjust thresholds if needed

## Security Considerations

1. **Token Verification**: Always verify server-side, never trust client
2. **Rate Limiting**: Limit Turnstile verification attempts
3. **Token Expiry**: Tokens expire after 10 minutes
4. **IP Binding**: Tokens are IP-bound
5. **Audit Logging**: Log all verification attempts

## Monitoring & Alerting

### Metrics
- `turnstile_verification_success_rate`
- `turnstile_verification_latency_p99`
- `captcha_failure_rate_by_endpoint`
- `burst_detection_rate`

### Alerts
- Alert if success rate drops below 99%
- Alert if latency exceeds 500ms
- Alert if failure rate exceeds 5%

## Open Questions

1. Should we implement a fallback CAPTCHA provider?
2. How should we handle Turnstile outages?
3. What's the optimal burst detection window?
4. Should we cache feature flag checks?

## References

- [Cloudflare Turnstile Docs](https://developers.cloudflare.com/turnstile/)
- [HU-A08](../../docs/HU/Auth/HU-A08-CAPTCHA en registro y votos sospechosos.md)
- [PostHog Feature Flags](https://posthog.com/docs/feature-flags)
