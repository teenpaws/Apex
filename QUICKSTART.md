# Apex — Quickstart Guide

Get Apex running locally in ~30 minutes.

## Prerequisites

- Docker Desktop installed and running
- A Supabase account (free at https://supabase.com)
- An Anthropic API key (https://console.anthropic.com)
- An OpenAI API key (https://platform.openai.com)

## Step 1: Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/apex.git
cd apex
```

## Step 2: Set up Supabase

1. Create a new Supabase project at https://supabase.com
2. Go to **SQL Editor** and paste the contents of `schema/initial.sql`
3. Click **Run** — this creates all tables and RLS policies
4. Find your keys in **Settings → API**:
   - Project URL
   - anon public key
   - service_role secret key
   - Database connection string (Settings → Database → Connection string → URI)

## Step 3: Get free API keys (5 minutes)

| Service | Sign up | What for |
|---------|---------|----------|
| Anthropic | https://console.anthropic.com | AI agents (required) |
| OpenAI | https://platform.openai.com | Embeddings (required) |
| NewsData.io | https://newsdata.io/register | Signal ingestion (free 200/day) |
| GNews | https://gnews.io/register | Signal backup (free 100/day) |
| PDL | https://dashboard.peopledatalabs.com/signup | Contact enrichment (free 1k/mo) |
| Hunter.io | https://hunter.io/users/sign_up | Email finding (free 25/mo) |
| Adzuna | https://developer.adzuna.com | Job validation (free) |

## Step 4: Run the setup script

```bash
./start.sh
```

This will:
1. Copy `.env.example` → `.env` and prompt you to fill it in
2. Build and start all Docker services
3. Seed demo data so your first experience is non-empty

## Step 5: Open Apex

- Frontend: http://localhost:3000
- Log in with the `OWNER_EMAIL` / `OWNER_PASSWORD` you set in `.env`
- Click **Run Pipeline** on the dashboard to ingest your first signals

## Troubleshooting

**Backend won't start:** `docker-compose logs backend` to see the error.

**"placeholder" errors in logs:** Your `.env` has unfilled placeholder values. Open `.env` and replace them.

**Signals aren't ingesting:** Check your `NEWSDATA_API_KEY` is valid. Test at https://newsdata.io/api-science.

**Something else:** Paste the error into Claude and ask for help. Seriously — that's the documented support path.
