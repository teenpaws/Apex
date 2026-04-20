# Apex Platform

Multi-agent AI platform that predicts hiring 4–12 weeks before roles are posted.

## Quick Start (Production)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Supabase project at https://supabase.com
- API keys configured (see Environment Setup below)

### 1. Clone and configure environment

```bash
git clone <repo-url> apex && cd apex
cp backend/.env.prod.example backend/.env.prod
# Edit backend/.env.prod — fill in all API keys and Supabase credentials
```

### 2. Run database migrations

```bash
DATABASE_URL=<your-supabase-db-url> bash backend/scripts/run_migrations.sh
```

### 3. Launch the stack

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Verify everything is running

```bash
# All containers healthy
docker compose -f docker-compose.prod.yml ps

# API responds
curl http://localhost/api/v1/health
# Expected: {"status":"ok","version":"1.0.0","environment":"production","mock_mode":false}

# Open in browser
open http://localhost
```

---

## Environment Setup

| Variable | Where to Get It | Required |
|----------|----------------|----------|
| `SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API | ✅ |
| `DATABASE_URL` | Supabase → Settings → Database | ✅ |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com | ✅ |
| `OPENAI_API_KEY` | https://platform.openai.com | ✅ |
| `NEWSDATA_API_KEY` | https://newsdata.io/register (free, 200/day) | ✅ |
| `GNEWS_API_KEY` | https://gnews.io/register (free, 100/day) | ✅ |
| `PDL_API_KEY` | https://dashboard.peopledatalabs.com (free, 1k/mo) | ✅ |
| `HUNTER_API_KEY` | https://hunter.io (free, 25/mo) | ✅ |
| `GMAIL_CLIENT_ID` + `GMAIL_CLIENT_SECRET` | Google Cloud Console → OAuth 2.0 | For email |
| `ALLOWED_ORIGINS` | Your frontend domain, e.g. `["https://app.example.com"]` | ✅ |

All API keys have free tiers sufficient for personal-scale usage. See `CLAUDE.md` Section 14 for details.

---

## Development (No Docker Required)

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload
# API docs: http://localhost:8000/api/docs

# Frontend
cd frontend && npm install && npm run dev
# UI: http://localhost:3000

# Run backend tests
cd backend && pytest tests/ -q --tb=short -k "not test_db"

# Run frontend tests
cd frontend && npm test
```

---

## Architecture

```
Internet → Nginx :80
  ├── /api/* → FastAPI (Gunicorn + UvicornWorker) :8000
  └── /*     → Next.js standalone :3000

FastAPI ←→ Supabase Postgres (cloud, pgvector)
FastAPI ←→ Redis :6379
Celery worker ←→ Redis  (signal processing)
Celery beat   ←→ Redis  (4h ingest cron)
```

---

## Stopping the Stack

```bash
docker compose -f docker-compose.prod.yml down       # stop, keep data
docker compose -f docker-compose.prod.yml down -v    # stop + delete Redis volume
```
