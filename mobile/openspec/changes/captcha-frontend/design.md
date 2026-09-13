# Design: Frontend TurnstileWidget — HU-A08

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   TurnstileWidget                     │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  @marsidev/react-turnstile                     │  │   │
│  │  │  - siteKey: string                             │  │   │
│  │  │  - onSuccess: (token) => void                  │  │   │
│  │  │  - onError: (error) => void                    │   │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐               │
│         │                 │                 │                │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐        │
│  │ Registration│  │  Vote Page  │  │  Settings   │        │
│  │    Page     │  │             │  │   Panel     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. TurnstileWidget Component

```tsx
// src/components/auth/TurnstileWidget.tsx

import { Turnstile } from '@marsidev/react-turnstile';

interface TurnstileWidgetProps {
  siteKey: string;
  onSuccess: (token: string) => void;
  onError?: (error: string) => void;
  onExpire?: () => void;
  theme?: 'light' | 'dark' | 'auto';
  size?: 'normal' | 'compact';
}

export function TurnstileWidget({
  siteKey,
  onSuccess,
  onError,
  onExpire,
  theme = 'auto',
  size = 'normal',
}: TurnstileWidgetProps) {
  return (
    <Turnstile
      siteKey={siteKey}
      onSuccess={onSuccess}
      onError={onError}
      onExpire={onExpire}
      theme={theme}
      size={size}
      options={{
        appearance: 'interaction-only', // Invisible unless needed
      }}
    />
  );
}
```

### 2. Registration Integration

```tsx
// src/pages/auth/RegisterPage.tsx

import { TurnstileWidget } from '@/components/auth/TurnstileWidget';

export function RegisterPage() {
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  
  const handleOAuthLogin = async (provider: 'google' | 'github') => {
    if (!turnstileToken) {
      // Show error
      return;
    }
    
    // Redirect to OAuth with token
    window.location.href = `/auth/login/${provider}?turnstile_token=${turnstileToken}`;
  };
  
  return (
    <div>
      <h1>Sign up</h1>
      
      <TurnstileWidget
        siteKey={import.meta.env.VITE_TURNSTILE_SITE_KEY}
        onSuccess={setTurnstileToken}
      />
      
      <button onClick={() => handleOAuthLogin('google')}>
        Sign up with Google
      </button>
      
      <button onClick={() => handleOAuthLogin('github')}>
        Sign up with GitHub
      </button>
    </div>
  );
}
```

### 3. Voting Integration

```tsx
// src/components/voting/VoteButton.tsx

import { TurnstileWidget } from '@/components/auth/TurnstileWidget';

interface VoteButtonProps {
  categoryId: string;
  targetId: string;
  targetType: string;
  isFirstVote: boolean;
  isBurst: boolean;
}

export function VoteButton({
  categoryId,
  targetId,
  targetType,
  isFirstVote,
  isBurst,
}: VoteButtonProps) {
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [showTurnstile, setShowTurnstile] = useState(false);
  
  const needsTurnstile = isFirstVote || isBurst;
  
  const handleVote = async () => {
    if (needsTurnstile && !turnstileToken) {
      setShowTurnstile(true);
      return;
    }
    
    await vote({
      categoryId,
      targetId,
      targetType,
      turnstileToken,
    });
  };
  
  return (
    <div>
      {showTurnstile && (
        <TurnstileWidget
          siteKey={import.meta.env.VITE_TURNSTILE_SITE_KEY}
          onSuccess={setTurnstileToken}
        />
      )}
      
      <button onClick={handleVote}>
        Vote
      </button>
    </div>
  );
}
```

## Configuration

### Environment Variables
```env
VITE_TURNSTILE_SITE_KEY=0x...
```

## Testing Strategy

### Unit Tests
- Test TurnstileWidget renders
- Test token callback fires
- Test error handling

### Integration Tests
- Test registration flow with Turnstile
- Test voting flow with Turnstile
- Test error scenarios

## Rollout Plan

### Phase 1: Component (Day 1)
- Create TurnstileWidget
- Add to storybook

### Phase 2: Registration (Day 2)
- Integrate with registration page
- Test OAuth flow

### Phase 3: Voting (Day 3)
- Integrate with vote button
- Test first vote and burst detection
