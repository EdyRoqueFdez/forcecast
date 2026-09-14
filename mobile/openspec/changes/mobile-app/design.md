# Design: Forcecast Mobile App — Technical Architecture

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Mobile App (Expo)                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                    UI Layer                          │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │ │
│  │  │  Vote   │ │Rankings │ │ Models  │ │ Profile │  │ │
│  │  │ Screen  │ │ Screen  │ │ Screen  │ │ Screen  │  │ │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │ │
│  └───────┼───────────┼───────────┼───────────┼────────┘ │
│          │           │           │           │           │
│  ┌───────▼───────────▼───────────▼───────────▼────────┐ │
│  │                 State Management                     │ │
│  │  ┌─────────────────────────────────────────────┐   │ │
│  │  │              Zustand Store                    │   │ │
│  │  │  - authStore (tokens, user)                  │   │ │
│  │  │  - modelsStore (models, filters)             │   │ │
│  │  │  - votingStore (votes, rankings)             │   │ │
│  │  │  - uiStore (theme, language, loading)        │   │ │
│  │  └─────────────────────────────────────────────┘   │ │
│  └───────────────────────┬────────────────────────────┘ │
│                          │                               │
│  ┌───────────────────────▼────────────────────────────┐ │
│  │                   API Layer                         │ │
│  │  ┌─────────────────────────────────────────────┐   │ │
│  │  │              API Client                      │   │ │
│  │  │  - Base URL configuration                   │   │ │
│  │  │  - Auth headers injection                   │   │ │
│  │  │  - Token refresh logic                      │   │ │
│  │  │  - Error handling                           │   │ │
│  │  │  - Retry logic                              │   │ │
│  │  └─────────────────────────────────────────────┘   │ │
│  └───────────────────────┬────────────────────────────┘ │
│                          │                               │
│  ┌───────────────────────▼────────────────────────────┐ │
│  │                 Storage Layer                       │ │
│  │  ┌─────────────┐  ┌─────────────┐                 │ │
│  │  │ expo-secure │  │  AsyncStorage│                 │ │
│  │  │   -store    │  │  - cache     │                 │ │
│  │  │   - tokens  │  │  - settings  │                 │ │
│  │  │   - user    │  │  - offline   │                 │ │
│  │  └─────────────┘  └─────────────┘                 │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Backend API (FastAPI)                        │
│  - /api/v1/models/*                                      │
│  - /auth/*                                               │
│  - /voting/*                                             │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

### Core
- **Expo SDK 52** — React Native framework
- **Expo Router** — File-based navigation
- **React Native** — UI framework

### State Management
- **Zustand** — Lightweight state management
- **React Query (TanStack Query)** — Server state management

### Storage
- **expo-secure-store** — Secure token storage
- **AsyncStorage** — Cache and settings

### UI
- **React Native Reanimated** — Animations
- **React Native Gesture Handler** — Touch interactions
- **expo-haptics** — Haptic feedback

### API
- **fetch** — HTTP client (built-in)
- **expo-auth-session** — OAuth flows

## Project Structure

```
mobile/
├── app/                    # Expo Router pages
│   ├── (auth)/             # Auth group
│   │   ├── login.tsx
│   │   └── register.tsx
│   ├── (tabs)/             # Main tabs
│   │   ├── vote.tsx
│   │   ├── rankings.tsx
│   │   ├── models.tsx
│   │   └── profile.tsx
│   ├── _layout.tsx         # Root layout
│   └── index.tsx           # Entry redirect
├── components/             # Reusable components
│   ├── ui/                 # Design system atoms
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Badge.tsx
│   │   ├── Avatar.tsx
│   │   ├── Chip.tsx
│   │   ├── Toggle.tsx
│   │   ├── Card.tsx
│   │   ├── Modal.tsx
│   │   ├── Tabs.tsx
│   │   ├── Skeleton.tsx
│   │   └── Toast.tsx
│   ├── features/           # Feature components
│   │   ├── VoteCard.tsx
│   │   ├── ComparisonCard.tsx
│   │   ├── EloBadge.tsx
│   │   ├── ModelItem.tsx
│   │   └── RankItem.tsx
│   └── layout/             # Layout components
│       ├── Navbar.tsx
│       ├── BottomNav.tsx
│       └── ScreenContainer.tsx
├── stores/                 # Zustand stores
│   ├── authStore.ts
│   ├── modelsStore.ts
│   ├── votingStore.ts
│   └── uiStore.ts
├── api/                    # API layer
│   ├── client.ts           # Base client
│   ├── auth.ts             # Auth API
│   ├── models.ts           # Models API
│   ├── voting.ts           # Voting API
│   └── types.ts            # API types
├── hooks/                  # Custom hooks
│   ├── useAuth.ts
│   ├── useModels.ts
│   ├── useVoting.ts
│   └── useTheme.ts
├── lib/                    # Utilities
│   ├── constants.ts
│   ├── i18n.ts
│   └── theme.ts
├── assets/                 # Static assets
│   ├── fonts/
│   └── images/
└── app.json                # Expo config
```

## Key Design Decisions

### 1. File-based Routing (Expo Router)
- Each screen is a file in `app/`
- Tab navigation via `(tabs)` group
- Auth guard via layout wrappers

### 2. Server State (React Query)
- Cache API responses
- Background refetch
- Optimistic updates for votes
- Offline support

### 3. Token Management
- Store in expo-secure-store
- Auto-refresh before expiry
- Attach to all API requests
- Clear on logout

### 4. Theme System
- 4 themes: dark/light × emerald/jedi
- CSS variables via StyleSheet
- Persist preference in AsyncStorage
- System theme detection

### 5. i18n
- Simple key-based translation
- EN/ES support
- Dynamic language switching
- Persist preference

## Data Flow

### Vote Flow
```
User taps Vote
  → VoteCard.onVote(modelSlug)
  → votingStore.castVote(eventId, modelSlug)
  → api.voting.createVote()
  → POST /voting/votes
  → Update local state
  → Show toast
  → Load next pair
```

### Rankings Flow
```
Screen loads
  → useRankings(category)
  → GET /voting/rankings?category={cat}
  → Cache response
  → Render list
  → Pull to refresh → refetch
```

### Auth Flow
```
User taps Login
  → api.auth.login(email, password)
  → POST /auth/login
  → Store tokens in SecureStore
  → authStore.setAuthenticated(true)
  → Redirect to tabs
```

## Error Handling Strategy

### Network Errors
- Show offline snackbar
- Queue actions for retry
- Use cached data

### API Errors
- Show toast with error message
- 401 → refresh token → retry
- 403 → show permission error
- 500 → show server error

### Validation Errors
- Show inline errors
- Highlight invalid fields
- Prevent submission

## Performance Considerations

1. **Lazy Loading** — Load screens on demand
2. **Image Caching** — Cache avatar images
3. **List Optimization** — Use FlatList for large lists
4. **Debounced Search** — Debounce search input
5. **Optimistic Updates** — Update UI before API response

## Security Considerations

1. **Token Storage** — Use expo-secure-store
2. **API Communication** — HTTPS only
3. **Input Validation** — Validate all inputs
4. **Error Messages** — Don't expose internal errors
