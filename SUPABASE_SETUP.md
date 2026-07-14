# Supabase Setup Guide

Complete steps to connect this project to a Supabase PostgreSQL database.
Takes about 10 minutes.

---

## 1. Create a Supabase project

1. Go to https://supabase.com → **New project**
2. Name it `zepto-clone`, choose a strong database password, pick region
   closest to you (e.g. `ap-south-1` for India)
3. Wait ~2 minutes for provisioning

---

## 2. Get your connection strings

In Supabase dashboard → **Settings** → **Database**:

| Use case | Where to find | Port |
|---|---|---|
| Run app (Railway/Vercel) | Connection pooling → Transaction mode | **6543** |
| Run migrations / seed | Direct connection | **5432** |

Copy the **Transaction Pooler** string — it looks like:
```
postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

---

## 3. Set up your local .env

```bash
cd backend
cp .env.example .env
```

Edit `.env`:
```env
# Transaction pooler (for running the app):
DATABASE_URL=postgresql+asyncpg://postgres.xxxxxxxxxxxx:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

# Direct connection (for migrations + seed — note port 5432):
# DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres

ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
```

---

## 4. Run migrations

Use the **Direct** connection string for migrations (pgBouncer doesn't
support DDL statements):

```bash
cd backend

# Temporarily switch to direct connection for migrations
export DATABASE_URL="postgresql+asyncpg://postgres:[PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres"

pip install alembic aiosqlite
alembic upgrade head
```

You should see:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
```

Verify in Supabase dashboard → **Table Editor** — you should see:
`departments`, `products`, `users`, `user_events`, `orders`, etc.

---

## 5. Seed the database

Still using the **Direct** connection:

```bash
# Make sure the ML artifacts exist first
python ml_research/02_collaborative_filtering.py
python ml_research/03_content_embeddings.py

# Seed products, categories, promo codes
python seed_db.py
```

Expected output:
```
✅  Seeded 33 products across 7 categories
✅  Seeded 4 promo codes
```

Verify in Supabase → Table Editor → `products` — should show 33 rows with
real Zepto CDN image URLs.

---

## 6. Run the backend locally against Supabase

Switch back to the Transaction Pooler URL in your `.env`, then:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Test it:
```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","db":"connected",...}

curl http://localhost:8000/api/v1/products | python -m json.tool | head -30
# → array of 33 real Zepto products

curl http://localhost:8000/api/v1/recommend/global/trending
# → {"products":[...],"source":"trending"}
```

---

## 7. Deploy backend to Railway pointing at Supabase

1. Push your repo to GitHub
2. Go to https://railway.app → **New Project** → **Deploy from GitHub repo**
3. Select the repo, set root directory to `backend/`
4. In Railway → **Variables**, add:
   ```
   DATABASE_URL  = <Supabase Transaction Pooler URL, port 6543>
   REDIS_URL     = <Upstash Redis URL or Railway Redis addon>
   ANTHROPIC_API_KEY = sk-ant-...
   SECRET_KEY    = <your secret>
   ALLOWED_ORIGINS = https://your-app.vercel.app
   ```
5. Railway auto-detects the Dockerfile and deploys

---

## 8. Deploy frontend to Vercel pointing at Railway

```bash
cd frontend
echo "VITE_API_URL=https://your-railway-backend.up.railway.app/api/v1" > .env.production
```

Then deploy:
```bash
npx vercel --prod
```

Or connect your GitHub repo to Vercel and add the env var in the Vercel
dashboard under **Settings** → **Environment Variables**.

---

## Troubleshooting

**"SSL connection is required"** — Supabase requires SSL. The `asyncpg`
driver negotiates SSL automatically. If you see this, make sure you're
using `postgresql+asyncpg://` (not `psycopg2://`).

**"prepared statement does not exist"** — You're using the Transaction
Pooler (port 6543) for a query that requires prepared statements. Switch
to the Direct connection (port 5432) or the Session Pooler.

**"too many connections"** — Use the Transaction Pooler (port 6543). The
free Supabase tier has a 60-connection limit; the pooler multiplexes them.

**seed_db.py hangs** — asyncpg can hang if the Supabase project is paused
(free tier pauses after 1 week of inactivity). Wake it up in the Supabase
dashboard → **Overview** → **Restore project**.
