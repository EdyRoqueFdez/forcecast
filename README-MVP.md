# Forcecast MVP — Deploy & Validation Guide

**Goal:** Deploy a working AI model comparator in ~30 min, validate with real users for 14 days, then decide: continue / pivot / discard.

---

## 🏗 Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Frontend       │────▶│  Backend API    │
│  (Vercel)       │     │  (Fly.io)       │
│  index.html     │     │  FastAPI        │
│  vanilla JS     │     │  in-memory JSON │
└─────────────────┘     └─────────────────┘
```

- **No database** — models loaded from `app/data/models.json` at startup
- **No auth** — completely open
- **No billing** — prices are reference only
- **CORS enabled** — frontend can call API from anywhere

---

## 🚀 Quick Deploy (Backend → Fly.io)

### Prerequisites
- [Fly.io CLI](https://fly.io/docs/hands-on/install-flyctl/) installed & logged in (`fly auth login`)
- Git repo initialized (already done in `backend/`)

### Deploy Commands

```bash
cd forcecast/backend

# 1. Launch app (creates fly.toml if missing, provisions VM)
fly launch --name forcecast-mvp --region mad --no-deploy

# 2. Deploy
fly deploy

# 3. Verify
fly open  # opens https://forcecast-mvp.fly.dev/health
curl https://forcecast-mvp.fly.dev/api/v1/meta
```

### Expected Output
```json
{
  "categories": ["architecture", "coding", "debugging"],
  "providers": ["openai", "anthropic", "deepseek", "meta", "google", "alibaba"],
  "modalities": ["text", "vision", "reasoning", "audio"],
  "total_models": 7,
  "version": "0.1.0-mvp"
}
```

### Backend URL
**`https://forcecast-mvp.fly.dev`** — update `API_BASE` in frontend `index.html` line 348.

---

## 🌐 Quick Deploy (Frontend → Vercel)

### Option A: Vercel CLI (fastest)
```bash
cd forcecast/frontend-mvp
npx vercel --prod
# Follow prompts: link to existing project or create new
# Set "Output Directory" to "."
```

### Option B: Vercel Dashboard
1. Push `frontend-mvp/` to a GitHub repo
2. Import in Vercel → "Add New Project"
3. Framework: **Other** / "Static"
4. Output Directory: `.` (root)
5. Deploy

### Frontend URL
**`https://forcecast-mvp.vercel.app`** (or your custom domain)

---

## 🔧 Local Development

### Backend
```bash
cd forcecast/backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend
```bash
cd forcecast/frontend-mvp
python3 -m http.server 3000
# Open http://localhost:3000
# Edit index.html line 348: const API_BASE = "http://localhost:8000/api/v1";
```

### Run Tests
```bash
cd forcecast/backend
pytest app/tests/test_mvp.py -v
```

---

## 📊 What to Measure (14 Days)

| Metric | Tool | Target Signal |
|--------|------|---------------|
| Unique visitors | Plausible / GA4 | > 100 |
| Searches performed | Custom event | > 30% of visitors |
| Comparisons made | Custom event | > 15% of visitors |
| Return visits (7d) | Plausible / GA4 | > 20% |
| Waitlist signups | Formspree / Netlify Forms | > 10 |
| Feedback submissions | Formspree / Netlify Forms | > 5 qualitative |

### Add Analytics (2 min)
In `index.html` `<head>`, add:
```html
<!-- Plausible (privacy-friendly, $9/mo or self-host) -->
<script defer data-domain="forcecast-mvp.vercel.app" src="https://plausible.io/js/script.js"></script>

<!-- Or GA4 (free) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-XXXXXXXXXX');</script>
```

### Add Feedback Form (1 min)
Replace line 588 in `index.html`:
```javascript
window.open("https://forms.gle/YOUR_GOOGLE_FORM_ID", "_blank");
```
Or use **Formspree**: `<form action="https://formspree.io/f/YOUR_ID" method="POST">`

---

## ✅ Validation Checklist (Day 14)

| Question | Yes / No / Partial | Notes |
|----------|-------------------|-------|
| Do users search without guidance? | | |
| Do they compare ≥2 models? | | |
| Do they return for different tasks? | | |
| Do they ask for missing features? | | |
| Anyone willing to pay / leave email? | | |
| Is "coding" the dominant category? | | |
| Any model requested that's missing? | | |

### Decision Matrix

| Signals | Decision |
|---------|----------|
| ≥3 green + waitlist signups | **CONTINUE** → Resume SDD Taxonomy (phases 1-8) |
| 1-2 green, clear niche request | **PIVOT** → Rebuild for that niche (e.g., only coding) |
| All red, no engagement | **DISCARD** → Archive, try next idea from research |

---

## 🔄 After Validation: Resume SDD

If **CONTINUE**:

1. Switch back to `main` branch (or create `post-mvp` from `mvp-validation`)
2. The SDD artifacts in `backend/openspec/changes/taxonomy/` are ready
3. Run:
   ```bash
   # From forcecast/backend
   git checkout main
   # Merge any MVP fixes you want to keep
   # Then:
   sdd-apply taxonomy
   ```
4. Phase 1 (core logic) already has tests — they'll pass against real DB

---

## 🛠 Troubleshooting

| Issue | Fix |
|-------|-----|
| `fly deploy` fails | `fly logs` → check Dockerfile, Python version |
| CORS error in browser | Backend allows `*` — check `API_BASE` in `index.html` |
| Models not loading | `fly ssh console -C "cat app/data/models.json"` |
| Frontend 404 on refresh | Vercel `vercel.json` rewrites handle SPA — ensure `index.html` exists |
| Price shows `—` | Model has `null` price — that's correct for reference-only |

---

## 📁 File Map (MVP)

```
forcecast/
├── backend/                    # Fly.io deploy
│   ├── app/
│   │   ├── main.py            # FastAPI MVP (endpoints only)
│   │   ├── data/models.json   # 7 models, reference prices
│   │   └── tests/test_mvp.py  # 18 tests
│   ├── pyproject.toml         # Minimal deps (no DB)
│   ├── Dockerfile             # Fly.io build
│   └── fly.toml               # Fly.io config
│
├── frontend-mvp/              # Vercel deploy
│   ├── index.html             # Single-file app (HTML+CSS+JS)
│   └── vercel.json            # Vercel config
│
├── openspec/                  # SDD artifacts (preserved)
│   └── changes/taxonomy/      # Ready for post-MVP
│
└── README-MVP.md              # This file
```

---

## 🎯 Next Commands Summary

```bash
# 1. Backend deploy
cd forcecast/backend
fly launch --name forcecast-mvp --region mad --no-deploy
fly deploy

# 2. Update frontend API_BASE
# Edit forcecast/frontend-mvp/index.html line 348
# const API_BASE = "https://forcecast-mvp.fly.dev/api/v1";

# 3. Frontend deploy
cd ../frontend-mvp
npx vercel --prod

# 4. Test end-to-end
# Open https://your-frontend.vercel.app
# Search, filter, compare 2-4 models

# 5. Add analytics + feedback form
# 6. Share in communities
# 7. Wait 14 days → decide
```

---

**Ready? Run the commands above. Good luck! 🚀**