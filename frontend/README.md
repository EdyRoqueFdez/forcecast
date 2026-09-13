# Forcecast Frontend — React + TypeScript + Tailwind CSS

Modern, mobile-first React frontend for the Forcecast AI model comparator.

## 🛠 Tech Stack

- **React 19** + **TypeScript**
- **Vite** for fast dev/build
- **Tailwind CSS** for styling
- **Lucide React** for icons
- **clsx + tailwind-merge** for class composition

## 🚀 Quick Start

```bash
cd frontend

# Install dependencies
npm install

# Copy env and set API URL
cp .env.example .env.local
# Edit .env.local with your backend URL

# Start dev server
npm run dev
```

## 🏗 Build & Deploy

### Local Build
```bash
npm run build
npm run preview  # preview production build
```

### Deploy to Vercel (Recommended)
```bash
npx vercel --prod
```
Or connect your GitHub repo to Vercel for automatic deployments.

### Environment Variables (Vercel Dashboard)
| Variable | Value |
|----------|-------|
| `VITE_API_BASE` | `https://your-backend.fly.dev/api/v1` |

## 📁 Project Structure

```
src/
├── components/
│   ├── CompareBar.tsx      # Sticky compare bar (bottom)
│   ├── CompareModal.tsx    # Side-by-side comparison table
│   ├── Filters.tsx         # Search, category, provider, modality, sort
│   ├── LocaleSelector.tsx  # Language switcher (EN/ES/PT/FR/ZH)
│   ├── ModelCard.tsx       # Model display card
│   └── Toast.tsx           # Notification toasts
├── lib/
│   └── utils.ts            # formatPrice, formatNumber, cn, etc.
├── types.ts                # TypeScript interfaces
├── api.ts                  # API client
├── App.tsx                 # Main app component
├── main.tsx                # Entry point
└── index.css               # Tailwind + CSS variables
```

## 🌐 Features

- **i18n**: 5 languages (EN/ES/PT/FR/ZH) with browser detection
- **Responsive**: Mobile-first, works on all screen sizes
- **Real-time filtering**: Category, provider, modality, search
- **Sorting**: By release date, price, name
- **Comparison**: Select 2-4 models, view side-by-side table
- **Accessible**: Semantic HTML, ARIA labels, keyboard navigation
- **Dark mode**: Automatic via `prefers-color-scheme`

## 🔗 API Integration

Expects backend at `VITE_API_BASE` with endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/meta` | Categories, providers, modalities |
| `GET /api/v1/models` | List models (filter, sort, paginate) |
| `GET /api/v1/models/compare?slugs=a&slugs=b` | Compare 2-4 models |
| `GET /api/v1/models/{slug}` | Single model detail |

## 🧪 Testing

```bash
# Run linting
npm run lint

# Type check
npx tsc --noEmit
```

## 📱 Mobile-First Design

- Touch-friendly controls (44px minimum targets)
- Sticky compare bar at bottom
- Modal comparison with horizontal scroll
- Responsive grid: 1 col (mobile) → 4 col (xl)

## 🔧 Customization

### Colors (CSS Variables in `index.css`)
```css
:root {
  --accent: #00d4aa;      /* Primary brand color */
  --bg: #0b0d12;          /* Dark background */
  --card: #13161f;        /* Card background */
  /* ... */
}
```

### Add Languages
1. Add locale to `LOCALES` in `types.ts`
2. Add translations to `CATEGORY_TRANSLATIONS`
3. Add name to `LOCALE_NAMES`

## 📦 Production Checklist

- [ ] Set `VITE_API_BASE` in Vercel
- [ ] Add analytics (Plausible/GA4)
- [ ] Add feedback form (Formspree/Google Forms)
- [ ] Configure custom domain
- [ ] Enable Vercel Analytics/Speed Insights