# Design: HU-A03 — Email Verification

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Backend                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Auth API                            │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │  Register  │  │  Verify    │  │  Resend    │     │   │
│  │  │  Endpoint  │  │  Endpoint  │  │  Endpoint  │     │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘     │   │
│  │        │               │               │              │   │
│  │        └───────────────┼───────────────┘              │   │
│  │                        │                              │   │
│  │              ┌─────────▼─────────┐                    │   │
│  │              │  Email Service    │                    │   │
│  │              │  (Resend)         │                    │   │
│  │              └─────────┬─────────┘                    │   │
│  │                        │                              │   │
│  │              ┌─────────▼─────────┐                    │   │
│  │              │  Token Service    │                    │   │
│  │              │  (Redis/DB)       │                    │   │
│  │              └───────────────────┘                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Email Verification Token

```python
# app/auth/services/email_verification.py

import secrets
from datetime import datetime, timedelta, timezone

class EmailVerificationService:
    TOKEN_EXPIRY_HOURS = 24
    MAX_RESEND_PER_HOUR = 3
    
    async def generate_token(self, user_id: str) -> str:
        """Generate verification token."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.TOKEN_EXPIRY_HOURS)
        
        # Store in Redis/DB
        await self.store_token(user_id, token, expires_at)
        
        return token
    
    async def verify_token(self, token: str) -> str | None:
        """Verify token and return user_id."""
        # Get user_id from token
        user_id = await self.get_user_by_token(token)
        if not user_id:
            return None
        
        # Check expiry
        if await self.is_expired(token):
            return None
        
        # Mark as used
        await self.mark_used(token)
        
        return user_id
    
    async def can_resend(self, user_id: str) -> bool:
        """Check if user can resend (rate limit)."""
        count = await self.get_resend_count(user_id)
        return count < self.MAX_RESEND_PER_HOUR
```

### 2. Email Service

```python
# app/auth/services/email.py

from app.core.config import settings

class EmailService:
    async def send_verification(self, email: str, token: str) -> bool:
        """Send verification email via Resend."""
        verification_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}"
        
        try:
            await resend.emails.send({
                "from": "Forcecast <noreply@forcecast.app>",
                "to": email,
                "subject": "Verify your Forcecast account",
                "html": self._verification_template(verification_url),
            })
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            return False
    
    def _verification_template(self, url: str) -> str:
        return f"""
        <h1>Welcome to Forcecast!</h1>
        <p>Click the link below to verify your email:</p>
        <a href="{url}">Verify Email</a>
        <p>This link expires in 24 hours.</p>
        """
```

### 3. Verification Endpoint

```python
# app/auth/api/verification.py

@router.get("/auth/verify")
async def verify_email(token: str, db: AsyncSession = Depends(get_session)):
    """Verify email with token."""
    service = EmailVerificationService()
    
    user_id = await service.verify_token(token)
    if not user_id:
        raise HTTPException(400, "Invalid or expired token")
    
    # Update user
    user = await db.get(User, user_id)
    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    await db.commit()
    
    return {"message": "Email verified"}
```

### 4. Resend Endpoint

```python
@router.post("/auth/resend-verification")
async def resend_verification(
    body: ResendRequest,
    db: AsyncSession = Depends(get_session),
):
    """Resend verification email."""
    service = EmailVerificationService()
    
    # Check rate limit
    if not await service.can_resend(body.email):
        raise HTTPException(429, "Too many requests. Try again later.")
    
    # Get user
    user = await get_user_by_email(db, body.email)
    if not user:
        # Don't reveal if email exists
        return {"message": "If email exists, verification sent"}
    
    # Generate new token
    token = await service.generate_token(user.id)
    
    # Send email
    email_service = EmailService()
    await email_service.send_verification(user.email, token)
    
    return {"message": "If email exists, verification sent"}
```

### 5. Voting Gate

```python
# Update VoteService._validate_user

def _validate_user(self, user: User) -> None:
    """Validate user can vote (RG-03)."""
    if not user.email_verified:
        raise DomainError(
            "Email verification required to vote.",
            status_code=403,
        )
    if is_strict_mode(user):
        raise DomainError(
            "Bot signals detected. Voting restricted.",
            status_code=403,
        )
```

## Database Changes

### User Table (already exists)
No schema changes needed. `email_verified` and `email_verified_at` fields already exist.

### Verification Tokens (new)
```sql
CREATE TABLE email_verification_tokens (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Configuration

### Environment Variables
```env
# Email (Resend)
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@forcecast.app
FRONTEND_URL=http://localhost:5173

# Email Verification
EMAIL_VERIFICATION_EXPIRY_HOURS=24
EMAIL_VERIFICATION_MAX_RESEND=3
```

## Testing Strategy

### Unit Tests
- Test token generation
- Test token verification
- Test rate limiting
- Test expiry handling

### Integration Tests
- Test registration sends email
- Test verification flow
- Test resend flow
- Test voting gate

### E2E Tests
- Test complete registration flow
- Test verification link flow
