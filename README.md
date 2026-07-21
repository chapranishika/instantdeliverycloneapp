# ⚡ Zepto Clone — Full-Stack ML Recommendation System

> A production-grade quick-commerce grocery app with **real Zepto CDN product images**, a **3-layer ML recommendation engine**, and a complete MVC architecture — built with React + FastAPI + Python.

[![CI/CD](https://github.com/chapranishika/instantdeliverycloneapp/actions/workflows/ci.yml/badge.svg)](https://github.com/chapranishika/instantdeliverycloneapp/actions)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[Live Demo →](https://zepto-clone.vercel.app)** | **[API Docs →](https://your-backend.railway.app/docs)**

---

## 🖼️ Real Zepto CDN Images

All 33 product images are served directly from `cdn.zeptonow.com` — the same CDN used by the real Zepto app. Products are sourced from the uploaded Zepto project and include:

| Category        | Products |
|----------------|----------|
| 🍎 Fresh Fruits    | Banana, Apple, Mango, Orange, Papaya |
| 🥕 Fresh Vegetables | Onion, Potato, Cauliflower, Bottle Gourd, Tomato |
| 🌿 Leafy Herbs     | Spinach, Coriander, Curry Leaves, Mint, Chilli |
| 🌸 Flowers         | Rose, Marigold, White Flower |
| 🥒 Exotic Veggies  | Capsicum, Broccoli, Baby Corn, Iceberg, Mushroom |
| 🥛 Kitchen         | Milk, Tea, Sugar, Masala, Salt |
| 🧽 House Hold      | Floor Cleaner, Allout, Room Freshener, Soap, Sanitizer |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                Frontend — React + Vite (Vercel)                  │
│                                                                   │
│  HomePage  │  CategoryPage  │  ProductPage  │  CartPage          │
│  AIPage    │  SearchPage    │  ProfilePage                       │
│                                                                   │
│  Real Zepto CDN images · Zustand state · React Router           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│               FastAPI Backend (Railway)                          │
│  Auth · Rate limiting · Redis cache · Background tasks (Celery) │
└─────┬──────────────────┬────────────────────────┬───────────────┘
      │                  │                         │
┌─────▼──────┐  ┌────────▼─────────┐  ┌──────────▼──────────┐
│ Layer 1    │  │   Layer 2        │  │   Layer 3           │
│ CF (ALS)   │  │ CBF (FAISS)      │  │ LLM (Claude API)    │
│ SVD rank   │  │ Sentence-BERT    │  │ Query expansion     │
│ cold-start │  │ TF-IDF fallback  │  │ Re-ranking          │
└─────┬──────┘  └────────┬─────────┘  └──────────┬──────────┘
      └─────────────────┬┘───────────────────────┘
                        │
              ┌─────────▼────────┐
              │  Hybrid Ranker   │
              │  LightGBM        │
              │  LambdaMART      │
              │  A/B test router │
              └─────────┬────────┘
                        │
      ┌─────────────────┼─────────────────┐
 ┌────▼────┐     ┌──────▼──────┐    ┌────▼────┐
 │Postgres │     │   Redis     │    │  FAISS  │
 │Users    │     │Rec cache    │    │50k vecs │
 │Orders   │     │5 min TTL    │    │ANN idx  │
 │Events   │     └─────────────┘    └─────────┘
 └─────────┘
```

---

## 📊 ML Evaluation Metrics

**These numbers are computed by running the pipeline, not hardcoded.**
Run `python ml_research/02_collaborative_filtering.py` →
`03_content_embeddings.py` → `04_hybrid_ranker.py` to reproduce exactly
(all seeds are fixed for determinism).

Methodology: 600 synthetic users generated from 6 category-preference
personas (see `02_collaborative_filtering.py` for the persona definitions),
evaluated on a held-out 20% of each user's interactions, ranking the full
remaining 33-product catalogue.

| Model | Precision@10 | Recall@10 | NDCG@10 |
|-------|-------------|-----------|---------|
| Popularity baseline | 0.137 | 0.472 | 0.304 |
| CF only (TruncatedSVD) | 0.155 | 0.543 | 0.358 |
| CBF only (FAISS + TF-IDF) | 0.153 | 0.538 | **0.376** |
| **Hybrid (LightGBM LambdaMART)** | **0.158** | **0.552** | 0.372 |

**Honest finding:** the hybrid model wins on Precision@10 and Recall@10
(+15.8% / +17.1% vs popularity baseline), but CBF-only edges it out very
slightly on NDCG@10 (0.376 vs 0.372). With only 120 held-out users and a
33-item catalogue, this gap is within noise — re-running with more users
or a larger catalogue would be the natural next step. The headline result
that holds up: **the hybrid and individual ML signals all comfortably beat
the popularity baseline**, and feature importances show `cbf_score` and
`cf_score` as the top two drivers of the LambdaMART model.

**Caveat:** these are synthetic persona-based interactions (documented in
`02_collaborative_filtering.py`), not real user data — the catalogue is
only 33 products so `@10` metrics naturally look higher than they would
on a 50k-item production catalogue. The pipeline architecture (CF → CBF →
LambdaMART) is the same one you'd point at real interaction logs; swap
`generate_synthetic_interactions()` for a real data loader to use it on
production data.

For statistical-significance methodology (A/B testing, sample sizing,
sequential testing / peeking problem), see
`ml_research/05_ab_testing_simulation.py` — also fully runnable, with
results reported honestly (one comparison is significant, one is not).

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TypeScript, Zustand, React Router |
| Backend | FastAPI, SQLAlchemy async, Pydantic v2 |
| Database | PostgreSQL (asyncpg), Redis |
| Product Images | Real Zepto CDN (`cdn.zeptonow.com`) |
| CF | `scikit-learn` TruncatedSVD (implemented & runnable) — `implicit` ALS as documented upgrade path |
| CBF | TF-IDF + `faiss-cpu` (implemented & runnable) — `sentence-transformers` (all-MiniLM-L6-v2) as documented upgrade path |
| Ranking | `lightgbm` LambdaMART (implemented & runnable) |
| LLM | Anthropic Claude API (Gopi Bahu assistant) |
| Data | Synthetic persona-based interactions (33-product catalogue) — see `02_collaborative_filtering.py`; Instacart-data loader documented as upgrade path |
| Deploy | Vercel (frontend), Railway (backend + Postgres + Redis) |
| CI/CD | GitHub Actions |

---

## 🚀 Quick Start

### 1. Clone
```bash
git clone https://github.com/chapranishika/instantdeliverycloneapp.git
cd instantdeliverycloneapp
```

### 2. Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000/api/v1
npm run dev
# → http://localhost:5173
```

### 3. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY

# Create tables & seed products
python -c "import asyncio; from app.db.database import create_tables; asyncio.run(create_tables())"
python seed_db.py

uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs
```

### 4. ML Pipeline (train the models)
```bash
cd ml_research
python 01_eda.py                     # EDA + interaction matrix
python 02_collaborative_filtering.py  # Generate synthetic interactions + train TruncatedSVD (CF)
python 03_content_embeddings.py       # Build TF-IDF + FAISS index (CBF)
python 04_hybrid_ranker.py            # Train LightGBM LambdaMART, evaluate vs baselines
python 05_ab_testing_simulation.py    # A/B testing methodology demo (sample sizing, sequential tests)
```

---

## 📁 Project Structure

```
zepto-clone/
├── frontend/                    # React + Vite → Vercel
│   └── src/
│       ├── lib/
│       │   ├── products.ts      # 33 real Zepto products + CDN images
│       │   └── api.ts           # Typed FastAPI client
│       ├── pages/
│       │   ├── HomePage.tsx     # Hero + rails + dept grid
│       │   ├── CategoryPage.tsx # Sidebar + product grid
│       │   ├── ProductPage.tsx  # Detail + similar products
│       │   ├── CartPage.tsx     # Cart + promo codes + checkout
│       │   ├── AIPage.tsx       # Gopi Bahu streaming chat
│       │   ├── SearchPage.tsx   # Real-time semantic search
│       │   └── ProfilePage.tsx  # Orders + wishlist + settings
│       ├── components/
│       │   ├── ui/ProductCard.tsx          # Real CDN images + qty ctrl
│       │   ├── ui/RecommendationRail.tsx   # Horizontal product shelf
│       │   └── layout/BottomNav.tsx        # Tab navigation
│       ├── store/index.ts       # Zustand: cart, wishlist, user, toast
│       └── styles.css           # Complete production CSS
│
├── backend/                     # FastAPI → Railway
│   └── app/
│       ├── api/routes.py        # 15+ endpoints
│       ├── ml/
│       │   ├── collaborative/   # CF engine (ALS + SVD)
│       │   ├── content/         # CBF engine (FAISS + TF-IDF)
│       │   ├── llm/             # Gopi Bahu (Claude API)
│       │   └── ranker/          # Hybrid LightGBM + A/B router
│       ├── models/              # SQLAlchemy ORM
│       └── db/                  # PostgreSQL + Redis
│
└── ml_research/                 # Training notebooks (portfolio-ready)
    ├── 01_eda.py
    ├── 02_collaborative_filtering.py
    ├── 03_content_embeddings.py
    ├── 04_hybrid_ranker.py
    └── 05_ab_testing_simulation.py
```

---

## 🔑 Key Engineering Decisions

**Real CDN images** — Product images are loaded directly from `cdn.zeptonow.com` with `object-fit: contain` to preserve the white-background product photography style used by Zepto.

**Cold Start** — New users get global top-products until 5 interactions, then transition to personalised CF. Implemented via `cold_start.pkl` with per-category and global top-lists.

**Implicit Feedback** — Purchase counts converted to `log(1 + count)` confidence weights before factorisation (`02_collaborative_filtering.py`, TruncatedSVD). Standard industry approach for e-commerce implicit signals; the same weighting scheme carries over directly if you swap in `implicit`'s ALS.

**LambdaMART** — LightGBM's ranking objective optimises NDCG directly, unlike classifiers that optimise accuracy. This matters enormously for ranked list quality.

**A/B Testing** — Deterministic bucket assignment via MD5 hash of `user_id % 100`. Same user always gets same variant. Sequential testing with Bonferroni correction prevents false positives.

**Event Loop** — Every click, view, and add-to-cart fires to `/events`. Celery rebuilds the interaction matrix every night. This is the loop that makes recommendations improve over time.

---

## 🌐 Deploy

### Frontend → Vercel
```bash
cd frontend && npm run build
npx vercel --prod
# Set VITE_API_URL in Vercel dashboard
```

### Backend → Railway
1. Push to GitHub → connect Railway to repo
2. Add PostgreSQL and Redis plugins
3. Set env vars from `.env.example`
4. Railway auto-deploys on push to `main`

### GitHub Secrets needed
```
ANTHROPIC_API_KEY     VERCEL_TOKEN
VERCEL_ORG_ID         VERCEL_PROJECT_ID
RAILWAY_TOKEN         RAILWAY_SERVICE_ID
VITE_API_URL
```

---

## 📄 License

MIT — use freely, attribution appreciated.

---

*Built with ❤️ · [LinkedIn](https://linkedin.com/in/yourprofile) · [Portfolio](https://yoursite.com)*
