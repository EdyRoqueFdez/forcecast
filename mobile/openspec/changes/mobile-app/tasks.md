# Tasks: Forcecast Mobile App — Implementation Plan

## Overview
- **Total tasks**: 48
- **Estimated time**: ~20-25 hours
- **Phases**: 6
- **Risk level**: Medium (new platform, API integration)
- **Changed lines estimate**: ~3,500-4,000 lines

## Review Workload Forecast
- Chained PRs recommended: Yes
- 400-line budget risk: High
- Estimated changed lines: 3,500-4,000
- **Decision needed before apply: Yes** — Split into 8-10 chained PRs

---

## Phase 1: Project Setup (Est. 2-3h)

### 1.1 Initialize Expo Project
- [x] 1.1.1 Initialize Expo project with TypeScript template
- [x] 1.1.2 Configure Expo Router for file-based navigation
- [x] 1.1.3 Set up folder structure (app/, components/, stores/, api/, hooks/)
- [x] 1.1.4 Configure ESLint and Prettier
- [x] 1.1.5 Configure Jest and testing setup
- [x] 1.1.6 Create app.json with deep linking config

### 1.2 Install Dependencies
- [x] 1.2.1 Install state management (zustand, @tanstack/react-query)
- [x] 1.2.2 Install UI libraries (react-native-reanimated, react-native-gesture-handler)
- [x] 1.2.3 Install storage libraries (expo-secure-store, @react-native-async-storage/async-storage)
- [x] 1.2.4 Install utility libraries (expo-haptics, @expo/vector-icons)
- [x] 1.2.5 Install testing libraries (jest-expo, @testing-library/react-native)

**Gate checkpoint**: Project builds, tests run, navigation works.

---

## Phase 2: API Layer & Auth (Est. 4-5h)

### 2.1 API Client
- [x] 2.1.1 Create API client with base URL configuration
- [x] 2.1.2 Implement auth header injection
- [x] 2.1.3 Implement token refresh logic
- [x] 2.1.4 Implement retry logic for failed requests
- [x] 2.1.5 Create API types (interfaces for all endpoints)

### 2.2 Auth API
- [x] 2.2.1 Implement login endpoint (`POST /auth/login`)
- [x] 2.2.2 Implement register endpoint (`POST /auth/register`)
- [x] 2.2.3 Implement logout endpoint (`POST /auth/logout`)
- [x] 2.2.4 Implement OAuth GitHub flow (`GET /auth/github`)
- [x] 2.2.5 Implement OAuth Google flow (`GET /auth/google`)
- [x] 2.2.6 Implement token refresh endpoint (`POST /auth/refresh`)

### 2.3 Token Management
- [x] 2.3.1 Create secure token storage utility
- [x] 2.3.2 Implement token persistence across sessions
- [x] 2.3.3 Implement automatic token refresh on expiry
- [x] 2.3.4 Implement token clearing on logout

### 2.4 Auth Store
- [x] 2.4.1 Create Zustand auth store
- [x] 2.4.2 Implement login action
- [x] 2.4.3 Implement logout action
- [x] 2.4.4 Implement OAuth callback handling

**Gate checkpoint**: Auth flow works end-to-end, tokens persist.

---

## Phase 3: Design System (Est. 3-4h)

### 3.1 Theme System
- [x] 3.1.1 Create theme constants (colors, spacing, typography)
- [x] 3.1.2 Implement dark/light theme variants
- [x] 3.1.3 Implement emerald/jedi theme variants
- [x] 3.1.4 Create theme provider context
- [x] 3.1.5 Implement theme persistence

### 3.2 UI Components
- [x] 3.2.1 Create Button component
- [x] 3.2.2 Create Input component
- [x] 3.2.3 Create Badge component
- [x] 3.2.4 Create Avatar component
- [x] 3.2.5 Create Chip component
- [x] 3.2.6 Create Toggle component
- [x] 3.2.7 Create Card component
- [x] 3.2.8 Create Skeleton component
- [x] 3.2.9 Create Toast component

### 3.3 Layout Components
- [x] 3.3.1 Create Navbar component
- [x] 3.3.2 Create BottomNav component
- [x] 3.3.3 Create ScreenContainer component

### 3.4 i18n
- [x] 3.4.1 Create translation utility
- [x] 3.4.2 Add English translations
- [x] 3.4.3 Add Spanish translations
- [x] 3.4.4 Implement language toggle

**Gate checkpoint**: All UI components render correctly, theme switching works.

---

## Phase 4: Core Screens (Est. 6-8h)

### 4.1 Vote Screen
- [x] 4.1.1 Create VoteScreen component
- [x] 4.1.2 Create VoteCard component
- [x] 4.1.3 Create ComparisonCard component
- [x] 4.1.4 Create EloBadge component
- [x] 4.1.5 Create CategoryChip component
- [x] 4.1.6 Implement category selection
- [x] 4.1.7 Implement vote casting
- [x] 4.1.8 Implement skip functionality
- [x] 4.1.9 Implement progress tracking
- [x] 4.1.10 Add loading states

### 4.2 Rankings Screen
- [x] 4.2.1 Create RankingsScreen component
- [x] 4.2.2 Create RankItem component
- [x] 4.2.3 Create CategoryTabs component
- [x] 4.2.4 Implement rankings fetch
- [x] 4.2.5 Implement ELO display
- [x] 4.2.6 Implement pull to refresh
- [x] 4.2.7 Add loading states

### 4.3 Models Screen
- [x] 4.3.1 Create ModelsScreen component
- [x] 4.3.2 Create ModelItem component
- [x] 4.3.3 Create ModelDetailSheet component
- [x] 4.3.4 Implement search functionality
- [x] 4.3.5 Implement provider filter
- [x] 4.3.6 Implement model detail fetch
- [x] 4.3.7 Add loading states

### 4.4 Profile Screen
- [x] 4.4.1 Create ProfileScreen component
- [x] 4.4.2 Create StatsCard component
- [x] 4.4.3 Create RecentVotesList component
- [x] 4.4.4 Implement user fetch
- [x] 4.4.5 Implement stats calculation
- [x] 4.4.6 Implement edit profile
- [x] 4.4.7 Implement sign out
- [x] 4.4.8 Add loading states

### 4.5 Auth Screen
- [x] 4.5.1 Create LoginScreen component
- [x] 4.5.2 Create RegisterScreen component
- [x] 4.5.3 Implement email/password login
- [x] 4.5.4 Implement email/password register
- [x] 4.5.5 Implement OAuth buttons
- [ ] 4.5.6 Add form validation

**Gate checkpoint**: All screens render, navigation works, API calls succeed.

---

## Phase 5: Integration & Polish (Est. 3-4h)

### 5.1 Navigation
- [x] 5.1.1 Set up tab navigation
- [x] 5.1.2 Set up stack navigation for auth
- [x] 5.1.3 Implement deep linking
- [x] 5.1.4 Add screen transitions

### 5.2 API Integration
- [x] 5.2.1 Integrate Vote screen with API
- [x] 5.2.2 Integrate Rankings screen with API
- [x] 5.2.3 Integrate Models screen with API
- [x] 5.2.4 Integrate Profile screen with API

### 5.3 Error Handling
- [x] 5.3.1 Implement global error handler
- [x] 5.3.2 Add network status detection
- [x] 5.3.3 Add offline mode support
- [x] 5.3.4 Add retry logic for failed requests

### 5.4 Accessibility
- [x] 5.4.1 Add accessibility labels
- [x] 5.4.2 Add haptic feedback
- [x] 5.4.3 Test with screen reader

**Gate checkpoint**: App works end-to-end, error handling is robust.

---

## Phase 6: Testing & Polish (Est. 2-3h)

### 6.1 Unit Tests
- [x] 6.1.1 Write API client tests
- [x] 6.1.2 Write auth store tests
- [x] 6.1.3 Write voting store tests
- [x] 6.1.4 Write UI component tests

### 6.2 Integration Tests
- [x] 6.2.1 Write auth flow tests
- [x] 6.2.2 Write vote flow tests
- [x] 6.2.3 Write rankings flow tests

### 6.3 Performance
- [x] 6.3.1 Optimize list rendering
- [x] 6.3.2 Add image caching
- [x] 6.3.3 Test on low-end device

### 6.4 Final Polish
- [x] 6.4.1 Add all loading states
- [x] 6.4.2 Add all empty states
- [x] 6.4.3 Add all error states
- [x] 6.4.4 Final design review

**Gate checkpoint**: Tests pass, app is polished and ready.

---

## Dependency Graph

```
Phase 1: Setup
    ↓
Phase 2: API & Auth
    ↓
Phase 3: Design System
    ↓
Phase 4: Core Screens
    ↓
Phase 5: Integration
    ↓
Phase 6: Testing & Polish
```

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| OAuth deep linking | High | Test early, use expo-auth-session |
| Token refresh edge cases | High | Implement retry, handle concurrent requests |
| Performance on low-end | Medium | Optimize lists, lazy load screens |
| i18n completeness | Low | Use translation keys, fallback to EN |

## Success Criteria

- [ ] All 4 main screens render correctly
- [ ] Auth flow works end-to-end
- [ ] Votes are cast successfully
- [ ] Rankings display correctly
- [ ] Models can be searched and filtered
- [ ] Profile shows user data
- [ ] Theme switching works
- [ ] i18n works (EN/ES)
- [ ] All tests pass
- [ ] No critical bugs
