# Forcecast Mobile Mockups

Vanilla HTML/CSS/JS component library and screen mockups for Forcecast — a community-driven AI model ranking platform.

Zero dependencies. Just open `index.html` in a browser.

## Structure

```
mobile/mockups/
├── index.html              # Component catalog (entry point)
├── theme.css               # Dual-theme design tokens (emerald + Jedi/Force)
├── layout.css              # Container, grid, spacing, safe areas
├── utils.css               # Animations, skeleton shimmer, a11y helpers
├── app.js                  # Template engine, i18n (EN/ES), theme toggle, router
├── components/
│   ├── button.html         # Primary, ghost, danger, loading states
│   ├── input.html          # Text, search, textarea, error states
│   ├── badge.html          # Status, category, modality badges
│   ├── avatar.html         # Sizes, initials, provider colors, status
│   ├── chip.html           # Filter, category, removable chips
│   ├── rating.html         # Star rating (readonly + interactive)
│   ├── card.html           # Interactive, highlighted, stats cards
│   ├── modal.html          # Dialog, bottom sheet
│   ├── tabs.html           # Underline, pills, full-width tabs
│   ├── dropdown.html       # Custom select, native fallback
│   ├── skeleton.html       # Loading states with shimmer animation
│   ├── empty-state.html    # No data / first-time user states
│   ├── error-state.html    # 500, network, 404 error states
│   ├── vote-card.html      # Model vs model comparison (core UX)
│   ├── comparison-card.html # Multi-category bar comparison
│   ├── elo-badge.html      # ELO rating tier indicator
│   ├── progress.html       # Linear, circle, labeled progress
│   ├── toast.html          # Success, error, warning notifications
│   ├── navbar.html         # Top navigation bar
│   ├── bottom-nav.html     # Mobile bottom tab bar
│   └── footer.html         # Brand footer
└── screens/
    ├── vote.html           # Model comparison voting screen
    ├── rankings.html       # ELO leaderboard by category
    ├── models.html         # Browse all AI models
    └── profile.html        # User stats and vote history
```

## Themes

Two theme families, each with dark/light variants:

| Theme | Accent | Use case |
|-------|--------|----------|
| `dark` (default) | Emerald `#00d4aa` | Web dashboard |
| `light` | Emerald `#00a884` | Web light mode |
| `jedi-dark` | Blue `#4a9eff` + Gold `#ffd166` | Mobile/Force theme |
| `jedi-light` | Blue `#2563eb` + Gold `#d97706` | Mobile light |

Toggle via `data-theme` attribute on `<html>` or the theme button in the navbar.

## i18n

Built-in English and Spanish translations. Toggle with the globe icon or:

```js
FC.i18n.setLang('es');  // Switch to Spanish
FC.i18n.setLang('en');  // Switch to English
```

HTML elements with `data-i18n="key.path"` are auto-translated on language change.

## JS API (app.js)

```js
FC.init({ lang: 'en', theme: 'dark' });

// Navigation
FC.router.navigate('vote');
FC.router.onNavigate((screen) => console.log(screen));

// Theme
FC.theme.toggle();
FC.theme.set('jedi-dark');

// i18n
FC.i18n.t('vote.title');  // "Which model is better?"
FC.i18n.t('vote.match', { current: '7', total: '50' });  // "7 / 50"

// Toasts
FC.toast.show('success', 'Vote saved', 'Your vote has been recorded.');
FC.toast.show('error', 'Connection lost', '', 5000);

// Templates
FC.render('Hello {{name}}', { name: 'World' });  // "Hello World"
```

## ELO Tiers

| Range | Tier | Color |
|-------|------|-------|
| 1800+ | Elite | Gold |
| 1600–1799 | Strong | Green |
| 1400–1599 | Average | Gray |
| <1400 | Emerging | Muted |

## Design Principles

- **Mobile-first**: All components work at 320px–480px viewport widths
- **Safe areas**: Bottom nav respects `env(safe-area-inset-bottom)` for iPhone notch
- **Touch targets**: Minimum 44px tap targets per Apple HIG
- **Dual themes**: CSS custom properties enable runtime theme switching
- **Accessible**: ARIA roles, focus states, reduced-motion support
- **No dependencies**: Pure HTML/CSS/JS, no build step required

## Quick Start

```bash
# Open in browser
open mobile/mockups/index.html

# Or serve locally
npx serve mobile/mockups
```
