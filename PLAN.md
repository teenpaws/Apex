# PLAN.md — Apex Platform: Full Development Plan

> **Living document.** Update after every session. Mark tasks ✅ when complete.
> Last updated: 2026-04-26 | Phase 15: COMPLETE ✅ | Next: **Phase 16 — Action Page Revamp**
> Multi-user self-host distribution (Phases 20–24) planned — see `docs/superpowers/specs/2026-04-24-multi-user-self-host-design.md`

---

## Project Timeline Overview

| Phase | Name | Focus | BE Agents | FE Agents | QA Agents | Est. Sessions |
|-------|------|-------|-----------|-----------|-----------|--------------|
| 0 | Architecture Review & Approval | Design lock-in, no code | 0 | 0 | 0 | 1 |
| 0.5 | API Stack Audit & Remediation | Remove dead APIs, document free replacements | 0 | 0 | 0 | 1 |
| 1 | Project Foundation | Repo, DB schema, scaffolds | 1 | 1 | 1 | 2–3 |
| 2 | Core Backend APIs | Users, Companies, Signals CRUD | 2 | 0 | 1 | 3–4 |
| 3 | Signal Intelligence Engine | Ingestion workers, classifiers | 2 | 0 | 1 | 3–4 |
| 4 | AI Reasoning Layer | Opportunity prediction, fit scoring | 2 | 0 | 1 | 4–5 |
| 5 | People Intelligence | PDL enrichment, contacts, Hunter.io email finding | 1 | 0 | 1 | 2 |
| 6 | Frontend — Core Pages | Dashboard, Signals, Opportunities | 0 | 2 | 1 | 4–5 |
| 7 | Frontend — Action Pages | Actions, Outreach, Profile | 0 | 2 | 1 | 3–4 |
| 8 | Email Automation | Gmail OAuth, drafts, sends | 1 | 1 | 1 | 2–3 |
| 9 | Full Integration & E2E | Wire FE↔BE, real data | 1 | 1 | 2 | 3–4 |
| 10 | Testing & Hardening | Coverage, perf, security | 0 | 0 | 3 | 2–3 |
| 11 | v1.0 Deployment | Docker, prod config | 1 | 0 | 1 | 1–2 |
| 12 | Live Production Run | Signal ingestion live, classify + embed all signals, run full pipeline | 1 | 0 | 0 | 2–3 |
| 13 | Signal & Agent Quality (MVP) | SEC EDGAR date fix, NewsData logger, Celery concurrency, prompt rewrites | 1 | 0 | 0 | 1–2 |
| 14 | Post-MVP Enhancements | FE pipeline progress, Sonnet batch classifier, job board layer, launch package | 2 | 1 | 1 | 3–4 |
| 15 | Resume & Document Intelligence | Document upload, Profile Extractor Agent, seniority gate, enrich all agents | 2 | 1 | 1 | 3–4 |
| 16 | Action Page Revamp | Enrich actions with opp+signal context, company filter, intended_effect, FE redesign | 1 | 1 | 1 | 2–3 |
| 17 | Outreach Expansion | LinkedIn message gen, PDL URL surfacing, outreach channel routing | 1 | 1 | 1 | 2–3 |
| 18 | Signal Quality & Disambiguation | Domain-qualified search queries, pre-filter entity context matching | 1 | 0 | 1 | 2 |
| 19 | Analytics + Historical Backtesting | Wire analytics FE to real BE, backtesting framework (requires Phase 14 Adzuna) | 1 | 1 | 1 | 2–3 |
| 20 | Self-Host Foundations | Consolidated `initial.sql`, owner-bootstrap script, hardcode/config audit, SaaS-pivot readiness check | 1 | 0 | 1 | 2 |
| 21 | Railway Deploy Template | `railway.json`, service config, "Deploy on Railway" button, end-to-end smoke test | 1 | 0 | 1 | 1–2 |
| 22 | First-Run Setup Experience | `/system/status` endpoint, per-integration health tests, `/setup` wizard in FE | 1 | 1 | 1 | 2 |
| 23 | Non-Technical User Docs | `QUICKSTART.md` rewrite with screenshots, `API-KEYS.md`, `TROUBLESHOOTING.md`, `LICENSE` (MIT), `CONTRIBUTING.md`, `SECURITY.md` | 0 | 0 | 1 | 1–2 |
| 24 | Public Launch Polish | README polish + screenshots, GitHub Issues templates, CI for forks, optional anonymous install counter, demo seed data, cohort announcement | 1 | 1 | 1 | 1–2 |

**Total estimated sessions (with ~2hr model limit each): 60–80 sessions**

---

## Environment Setup Checklist

> Keys stored in `backend/.env` only — never committed to git.

| # | Dependency | Status | Notes |
|---|-----------|--------|-------|
| 1 | Anthropic API Key | ✅ Configured | All AI agents |
| 2 | OpenAI API Key | ✅ Configured | Embeddings (`text-embedding-3-small`) |
| 3 | NewsData.io Key | ✅ Configured | Primary news signal ingestion |
| 4 | GNews API Key | ✅ Configured | Backup news source |
| 5 | PDL API Key | ✅ Configured | Contact enrichment |
| 6 | Hunter.io Key | ✅ Configured | Email discovery by domain |
| 7 | Gmail OAuth Credentials | ✅ Configured | `GMAIL_CLIENT_ID` + `GMAIL_CLIENT_SECRET` |
| 8 | Supabase Project | ✅ Configured | URL + anon key + service role + DB URL |
| 9 | SEC EDGAR | ✅ No key needed | Public API — `data.sec.gov` |
| 10 | Mock flags disabled | ✅ Ready | `MOCK_AGENTS=false`, `USE_MOCK_DATA=false` |

---

## Git Branching Convention

Every phase is developed on its own branch and merged into `main` when complete.

```bash
# Start a phase
git checkout main && git pull origin main
git checkout -b phase/{N}-{short-name}
# e.g. phase/2-core-backend-apis

# Finish a phase — PR merge into main
git push origin phase/{N}-{short-name}
# Open PR on GitHub → review → merge → delete branch
```

| Branch pattern | Used for |
|----------------|---------|
| `main` | Stable, always-deployable code |
| `phase/{N}-{name}` | All work for Phase N (multiple commits OK) |

**Rule:** No direct commits to `main`. Every phase lands via a PR from its phase branch.

---

## Superpowers Setup (One-Time)

Before starting Phase 1, complete this setup:

```bash
# 1. Install superpowers framework
git clone https://github.com/obra/superpowers.git ~/.superpowers

# 2. Initialize git repo for Apex
cd "E:\Claude Projects\Apex"
git init
git add .
git commit -m "chore: initial commit — CLAUDE.md + PLAN.md + Index.tsx reference"

# 3. Create project structure directories
mkdir -p backend/app/{api,core,models,services,agents,workers,integrations,db}
mkdir -p backend/tests/{unit,integration,e2e}
mkdir -p frontend/app/\(dashboard\)/{signals,opportunities,actions,outreach,profile,analytics,settings}
mkdir -p frontend/{components/{ui,layout,signals,opportunities,actions,shared},lib,hooks,types}
```

---

## Phase 0: Architecture Review & Approval

**Goal:** Lock in architecture before writing a single line of code. Get explicit approval on data models, API design, and agent orchestration flow.

**Status:** ✅ COMPLETE — Approved 2026-04-12

### 0.1 Architecture Approval Checklist

- [x] **Data model review** — All tables confirmed. Added: `agent_runs`, `fit_score` on opportunities, `linkedin_url` on companies, `is_duplicate`/`dedup_hash` on signals, `reply_detected_at` on outreach_emails.
- [x] **API design review** — Endpoints confirmed. Added: `GET /agents/run-status/{run_id}`, `GET /agents/runs`, `GET /analytics/costs`, `POST /contacts/search`, `GET /contacts/{id}`, `GET /health`, `POST /auth/refresh`, Gmail OAuth endpoints.
- [x] **Agent orchestration review** — 6-agent design confirmed. Contact Identifier merged into Opportunity Predictor. Career Fit Scorer + Positioning Advisor run in parallel. Mock mode via `MOCK_AGENTS=true`.
- [x] **Signal sources review** — Priority for v1.0: NewsAPI + RSS Feeds + SEC EDGAR (free/low-cost). Crunchbase + Proxycurl + Dealroom when API keys available.
- [x] **Frontend page scope review** — All 8 pages confirmed in scope for v1.0.
- [x] **Tech stack final confirmation** — Stack confirmed, no changes.
- [x] **Environment variables** — API keys to be provided later. All integrations built with mock mode (`USE_MOCK_DATA=true`, `MOCK_AGENTS=true`) until keys are available.
- [x] **Supabase project** — Connection strings to be provided later. DB schema and migrations built in Phase 1; applied when credentials available.

### 0.2 Decisions — LOCKED

| # | Decision | Resolution |
|---|----------|-----------|
| 1 | Auth scope | **Supabase Auth from day one** — cohort-ready; no hardcoded user |
| 2 | Signal ingestion trigger | **Both** — 4h cron (prod) + manual button (testing) |
| 3 | Email automation | **Draft + explicit confirm step** — user approves before any send |
| 4 | Analytics scope | **Dashboard stats only for v1.0** — full analytics page in v1.5 |

### 0.3 Architecture Approval Sign-Off

> **APPROVED ✅**
> 
> **Approved by:** Swapneet &nbsp;&nbsp;&nbsp; **Date:** 2026-04-12
> 
> **Changes from original design:**
> - `agent_runs` table added (audit + cost tracking)
> - `fit_score` field added to `opportunities`
> - `linkedin_url` added to `companies`
> - `Contact Identifier` agent merged into `Opportunity Predictor`
> - `Career Fit Scorer` + `Positioning Advisor` now run in parallel
> - Mock mode added (`MOCK_AGENTS`, `USE_MOCK_DATA` env flags)
> - `run_id` return pattern for all async endpoints
> - Signal source priority: NewsAPI + RSS + SEC EDGAR first
> - All API keys deferred — dev proceeds with mock data

---

## Detailed Architecture Reference

> Quick reference for developers. Full details in CLAUDE.md.

### Agent Pipeline (Final)
```
Signal Ingestion
  → Signal Classifier (Haiku) [GATE: relevance ≥ 0.4]
  → Opportunity Predictor (Sonnet) [outputs role + contact type]
  → [PARALLEL] Career Fit Scorer (Sonnet) + Positioning Advisor (Sonnet)
  → [JOIN]
  → Action Generator (Haiku)
  → agent_runs updated to SUCCESS

On demand: Email Drafter (Sonnet) → 3 tone variants
```

### Data Model Additions (vs. original)
```
companies        + linkedin_url
signals          + is_duplicate, dedup_hash
opportunities    + fit_score
outreach_emails  + reply_detected_at
agent_runs       NEW TABLE (full audit trail)
```

### Mock Development Strategy
```bash
# .env for development (no real API keys needed)
MOCK_AGENTS=true        # Agents return fixture JSON, no Claude calls
USE_MOCK_DATA=true      # API endpoints return mock_responses/, no DB calls

# When real keys available:
MOCK_AGENTS=false
USE_MOCK_DATA=false
# Zero code changes required
```

### Signal Source Priority (v1.0)
| Priority | Source | Reason |
|----------|--------|--------|
| 1 | RSS Feeds | Free, hourly, company-controlled content |
| 2 | SEC EDGAR | Free public API, Form D (funding) + 8-K (exec/contracts) |
| 3 | NewsData.io | Free 200/day, commercial OK, replaces NewsAPI.org |
| 4 | GNews API | Free 100/day, backup news source |
| 5 | PDL | Contact enrichment, free 1k/mo (replaces Proxycurl) |
| 6 | Hunter.io | Email finding, free 25/mo |

---

---

## Phase 0.5: API Stack Audit & Remediation

**Goal:** Remove dead/unavailable APIs from the stack before Phase 3 (Signal Intelligence) begins. Update CLAUDE.md and PLAN.md to reflect the free-tier replacement stack. No application code written in this phase — documentation and planning only.

**Status:** ✅ COMPLETE — 2026-04-12

**Trigger:** Pre-Phase 3 audit discovered three critical blockers in the planned API stack.

### What Changed

| Removed | Reason | Replacement |
|---------|--------|-------------|
| Proxycurl | Shut down July 2025, LinkedIn federal lawsuit | People Data Labs (PDL) — 1k free/mo |
| Crunchbase API | Enterprise-only (~$15k+/yr) | SEC EDGAR Form D filings (free, no key) |
| NewsAPI.org | Free tier localhost-only, unusable in prod | NewsData.io (200/day free, commercial OK) |
| Dealroom API | €6k+/yr minimum | Dropped — EU signals via NewsData.io + RSS |

### New Free-Tier Signal Stack

| Priority | Source | Cost | Key |
|----------|--------|------|-----|
| 1 | RSS Feeds | Free | None |
| 2 | SEC EDGAR (data.sec.gov) | Free | None |
| 3 | NewsData.io | Free 200/day | Free signup |
| 4 | GNews API | Free 100/day | Free signup |
| 5 | PDL (People Data Labs) | Free 1k/mo | Free signup |
| 6 | Hunter.io | Free 25/mo | Free signup |

### Impact on Upcoming Phases

**Phase 3 (Signal Intelligence Engine):** Sprint 3.1 tasks for `newsapi_client.py` and `crunchbase_client.py` must be replaced with `newsdata_client.py`, `gnews_client.py`, and `sec_edgar_client.py` (the SEC EDGAR client was already planned; now it also covers Form D funding data).

**Phase 5 (People Intelligence):** `proxycurl_client.py` must be replaced with `pdl_client.py` (People Data Labs) and `hunter_client.py` (email finding). The Proxycurl-based `enrich_contacts.py` worker must be rebuilt using PDL endpoints.

### Decisions Locked

| # | Decision | Resolution |
|---|----------|-----------|
| 1 | Contact enrichment provider | PDL (People Data Labs) — free 1k/mo, public data, legally clean |
| 2 | Funding data source | SEC EDGAR Form D (US) + NewsData.io press coverage (EU/global) |
| 3 | Primary news API | NewsData.io — commercial-friendly free tier, no delay |
| 4 | Dealroom | Dropped for v1.0. Revisit for v2.0 if EU coverage becomes insufficient. |
| 5 | Proxycurl replacement | PDL for enrichment + Hunter.io for email — no LinkedIn scraping at all |

---

## Phase 1: Project Foundation

**Goal:** Working repo with scaffolded BE + FE, Supabase schema deployed, Docker dev environment running.

**Status:** ✅ COMPLETE — Sprint 1.1 ✅ | Sprint 1.2 ✅

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (BE + FE + QA)

### Sprint 1.1 — Repository & Infrastructure (Session 1) ✅ COMPLETE

**Agent: BE Infrastructure Agent (1 agent)**

#### Tasks
- [x] Initialize Python project — used `pip + requirements.txt` (Poetry not available; Python 3.14.3)
- [x] Install: `fastapi`, `uvicorn[standard]`, `pydantic[email]`, `anthropic`, `httpx`, `python-jose`, `passlib` + test deps
- [x] Create `backend/app/core/config.py` — Settings class using Pydantic BaseSettings, reads from `.env`
- [x] Create `.env.example` with all required vars + `MOCK_AGENTS=true`, `USE_MOCK_DATA=true`
- [x] Create `backend/app/main.py` — FastAPI app with CORS, health router, `create_app()` factory
- [x] Create `backend/app/core/security.py` — JWT verify + Bearer extraction
- [x] Create `backend/app/core/dependencies.py` — `get_current_user()` with mock passthrough
- [x] Create `backend/app/api/v1/health.py` — `GET /api/v1/health`
- [x] Create `backend/app/agents/registry.py` — AGENT_REGISTRY (6 agents)
- [x] Create `backend/app/agents/base_agent.py` — BaseAgent ABC with retry + audit stub
- [x] Create all 6 agent fixture JSONs + 6 prompt stub files
- [x] All `__init__.py` files for every module
- [ ] ~~docker-compose.yml~~ — Docker not available on this machine; deferred
- [ ] ~~Dockerfile~~ — deferred with Docker

> **Note:** Docker not available on dev machine. `docker-compose.yml` and `Dockerfile` deferred.
> Dev server: `cd backend && uvicorn app.main:app --reload`

**Agent: FE Infrastructure Agent (1 agent)**

#### Tasks
- [x] Initialize Next.js 16.2.3 project with TypeScript + Tailwind + App Router
- [x] Install: `shadcn/ui`, `lucide-react`, `@supabase/supabase-js`, `@tanstack/react-query`, `axios`, `recharts`
- [x] Initialize shadcn/ui; install: `card`, `badge`, `progress`, `button`, `input`, `dialog`, `sheet`, `tabs`, `select`, `separator`
- [x] Migrate `Index.tsx` → `frontend/app/(dashboard)/page.tsx` (Next.js app router, Next.js Link)
- [x] Create `frontend/components/layout/DashboardLayout.tsx` — dark sidebar, 8-page nav, active state
- [x] Create `frontend/components/shared/PipelineViz.tsx` — pipeline stage overview
- [x] Create `frontend/lib/mock/index.ts` — full mock data (signals, opportunities, actions, companies, contacts, stats)
- [x] Create `frontend/types/index.ts` — full TypeScript interfaces for all models
- [x] Create `frontend/lib/api.ts` — axios client with auth interceptor
- [x] Create `frontend/app/(dashboard)/layout.tsx` — wraps DashboardLayout
- [x] Create stub pages: signals, opportunities, actions, outreach, profile, analytics, settings
- [x] Verify: `npm run build` compiles clean — all 11 routes static ✅

**Agent: QA Infrastructure Agent (1 agent)**

#### Tasks
- [x] Set up pytest with `pytest-asyncio`, `httpx`, `pytest-cov`
- [x] Set up Vitest + React Testing Library + `@testing-library/jest-dom` in frontend
- [x] Set up Playwright for E2E — chromium downloaded
- [x] Create `backend/tests/conftest.py` — async test client, mock user fixture
- [x] Create `backend/pytest.ini` — asyncio auto mode, coverage config
- [x] Write smoke tests: `GET /api/v1/health` → 200 ✅ (5/5 passing)
- [x] Write FE smoke test placeholder in `frontend/__tests__/dashboard.test.tsx`
- [x] Create `frontend/playwright.config.ts` + `frontend/e2e/dashboard.spec.ts`

### Sprint 1.2 — Database Schema (Session 2) ✅ COMPLETE

**Agent: BE Database Agent (1 agent)**

#### Tasks
- [x] Create Supabase migrations for all tables (CLAUDE.md Section 4):
  - [x] `users` table
  - [x] `career_profiles` table (with embedding vector[1536])
  - [x] `companies` table
  - [x] `contacts` table
  - [x] `signals` table (with embedding vector[1536])
  - [x] `opportunities` table
  - [x] `actions` table
  - [x] `outreach_emails` table
  - [x] `agent_runs` table
- [x] Enable Row Level Security on ALL tables (`011_create_rls_policies.sql`)
- [x] Create RLS policies: all SELECT/INSERT/UPDATE/DELETE filtered by `user_id = auth.uid()`
- [x] Create indexes: signals, opportunities, actions (`012_create_indexes.sql`)
- [x] Create pgvector IVFFlat index on `career_profiles.embedding` and `signals.embedding`
- [x] Python enums + SQLAlchemy ORM models + Pydantic v2 schemas for all 9 tables
- [x] Async DB session with lazy engine init (`backend/app/db/session.py`)
- [x] Seed dev data script: 1 test user, 5 companies, 10 signals, 3 opportunities, 5 actions
- [ ] ~~Run migrations against Supabase dev project~~ — deferred; no credentials yet (flip `USE_MOCK_DATA=false` when available)

> **Note:** All migrations written and ready. `python -c "from app.models import *"` passes. 7 integration tests exist, skipped under `USE_MOCK_DATA=true`. Existing 5 health tests still pass.

#### Verification
```bash
# Run from backend/
pytest tests/integration/test_db.py -v
# Tests skip cleanly under USE_MOCK_DATA=true
# Will run for real once Supabase credentials are configured
```

---

## Phase 2: Core Backend APIs

**Goal:** All CRUD endpoints for signals, opportunities, actions, profile, companies working with real Supabase data. Auth middleware working.

**Status:** ✅ COMPLETE — Sprint 2.1 ✅ | Sprint 2.2 ✅

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 BE + 1 QA) → `/test-driven-development`

**Pre-requisite:** Phase 1 complete ✅

### Sprint 2.1 — Auth & Base Setup (Session 3) ✅ COMPLETE

**Agent: BE Auth Agent (1 agent)**

#### Tasks
- [x] `backend/app/core/security.py` — JWT validation via Supabase (was already complete from Sprint 1.1)
- [x] `backend/app/core/dependencies.py` — `get_current_user` with mock passthrough (was already complete from Sprint 1.1)
- [x] `backend/app/core/errors.py` — `ErrorDetail`, `ApexHTTPException`, structured exception handlers
- [x] `backend/app/main.py` — register both exception handlers in `create_app()`
- [x] `backend/app/api/v1/auth.py` — `POST /auth/login` + `POST /auth/refresh` (mock + live Supabase paths)
- [x] `backend/app/api/v1/router.py` — auth router wired in
- [x] All endpoints return structured JSON errors via `ApexHTTPException`
- [x] Tests: 8 auth tests + 3 error shape tests — all pass (16 total, 7 DB skipped)

### Sprint 2.2 — Core Resource APIs (Sessions 4–5) ✅ COMPLETE

**Agent: BE API Agent A — Signals + Companies (1 agent)**

#### Tasks
- [x] `backend/app/models/signal.py` — already complete from Sprint 1.2
- [x] `backend/app/models/company.py` — already complete from Sprint 1.2
- [x] `backend/app/services/_mock_loader.py` — shared JSON loader
- [x] `backend/app/services/signal_service.py` — list/get/trigger_ingest with mock + live stubs
- [x] `backend/app/services/company_service.py` — get with attached signals
- [x] `backend/app/api/v1/signals.py` — `GET /signals`, `GET /signals/{id}`, `POST /signals/ingest`
- [x] `backend/app/api/v1/companies.py` — `GET /companies/{id}`
- [x] Mock fixtures: `signals.json`, `companies.json`

**Agent: BE API Agent B — Opportunities + Actions + Profile (1 agent)**

#### Tasks
- [x] `backend/app/models/opportunity.py` — already complete from Sprint 1.2
- [x] `backend/app/models/action.py` — already complete from Sprint 1.2
- [x] `backend/app/services/opportunity_service.py` — list/get/refresh with mock + live stubs
- [x] `backend/app/services/action_service.py` — list/update/draft_email
- [x] `backend/app/services/profile_service.py` — get/update
- [x] `backend/app/api/v1/opportunities.py` — `GET /opportunities`, `GET /opportunities/{id}`, `POST /{id}/refresh`
- [x] `backend/app/api/v1/actions.py` — `GET /actions`, `PUT /actions/{id}`, `POST /{id}/draft-email`
- [x] `backend/app/api/v1/profile.py` — `GET /profile`, `PUT /profile`
- [x] Mock fixtures: `opportunities.json`, `actions.json`, `profile.json`

**Agent: QA API Agent (1 agent)**

#### Tasks
- [x] 35 integration tests for all Sprint 2.2 endpoints (`test_api_endpoints.py`)
- [x] Tests for list, filter, get-by-id, 404, async task queueing (run_id)
- [x] All tests pass under `USE_MOCK_DATA=true` (51 total: 35 new + 16 existing, 7 DB skipped)

> **Note:** RLS and multi-user tests deferred to when real Supabase credentials are available. Live service stubs raise `NotImplementedError` — flip `USE_MOCK_DATA=false` to activate.

#### Phase 2 Verification
```bash
pytest tests/ -v --tb=short -k "not test_db"
# 51 passed, 7 skipped
```

---

## Phase 3: Signal Intelligence Engine

**Goal:** Automatic signal ingestion from all 5 sources, running on Celery workers, signals classified and stored in Supabase.

**Status:** ✅ COMPLETE — Sprint 3.1 ✅ | Sprint 3.2 ✅

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 BE + 1 QA)

**Pre-requisite:** Phase 2 complete ✅

### Sprint 3.1 — Signal Ingestion Workers (Sessions 6–7) ✅ COMPLETE

**Agent: BE Signal Ingestion Agent A (1 agent)**

#### Tasks
- [x] `backend/app/integrations/newsdata_client.py`
  - Primary news source — NewsData.io REST API
  - Redis cache 24h TTL per query; graceful 429 + network error handling (returns [])
  - `SignalEvent` dataclass defined here, shared by all clients
  - Mock mode returns deterministic FUNDING fixture
- [x] `backend/app/integrations/gnews_client.py`
  - Backup GNews API; same SignalEvent output schema
  - Mock mode returns deterministic EXEC_HIRE fixture
- [x] `backend/app/integrations/sec_edgar_client.py`
  - Form D filings: private funding rounds (FUNDING signals)
  - 8-K filings: exec changes / M&A (EXEC_HIRE or MA signals)
  - `User-Agent: Apex-Platform contact@apex.ai` required per SEC policy
  - `asyncio.sleep(0.12)` enforced after every request (10 req/s limit)
  - NO API KEY REQUIRED
- [x] `backend/app/integrations/rss_client.py`
  - feedparser via run_in_executor (sync lib kept off event loop)
  - Malformed/empty feeds handled gracefully (returns [])
- [x] `backend/app/workers/ingest_signals.py` (Celery tasks)
  - `ingest_from_newsdata`, `ingest_from_gnews`, `ingest_from_sec_edgar`, `ingest_from_rss`, `ingest_all_sources`
  - SHA-256 deduplication: `hash(source:external_id:date)` before every insert
  - Circular import guard for celery_app; module-level fallback functions for tests
  - `USE_MOCK_DATA=true`: skips all DB writes, logs what would be written

**Agent: BE Signal Ingestion Agent B (1 agent)**

#### Tasks
- [x] `backend/app/workers/classify_signals.py` (Celery tasks)
  - `classify_signal(signal_id)` — Haiku classification with 0.4 relevance gate
  - `batch_classify_signals(signal_ids[])` — fan-out pattern
  - `embed_signal(signal_id)` — 1536-dim vector (mock: zeros; live: OpenAI)
  - `classify_and_embed(signal_id)` — inline chain
- [x] `backend/app/core/celery_app.py` — Celery configuration
  - Beat schedule: `ingest_all_sources` every 4 hours
  - Priority queues: `high`, `default`, `low`
  - `task_acks_late=True`, `worker_prefetch_multiplier=1`

### Sprint 3.2 — Signal Classifier Agent (Session 8) ✅ COMPLETE

**Agent: BE AI Classification Agent (1 agent)**

#### Tasks
- [x] `backend/app/agents/signal_classifier.py`
  - `SignalClassifierInput` + `SignalClassifierOutput` Pydantic v2 models
  - `SignalClassifierAgent` extends BaseAgent; model from AGENT_REGISTRY (never hardcoded)
  - System prompt with prompt caching; dict input coercion for ergonomic test calls
  - `SignalClassifier = SignalClassifierAgent` alias exported
- [x] `backend/app/agents/base_agent.py` — enhanced
  - `_mock_mode: bool = True` class-level attribute (patchable by tests)
  - `write_agent_run()` public method + `_get_mock_output()` helper
- [x] `backend/app/agents/prompts/signal_classifier_v1.txt` — full system prompt
- [x] Snapshot tests for classifier via fixture file (FUNDING mock output)

**Agent: QA Signal Agent (1 agent)**

#### Tasks
- [x] Unit tests for each integration client (respx HTTP mocking, 7 test classes, ~60 tests)
- [x] Unit tests for signal_classifier agent (6 test classes, ~30 tests including retry)
- [x] Integration test: ingest → classify pipeline end-to-end
- [x] Test deduplication: same signal ingested twice → stored once
- [x] Test Celery task retry on API failures (mock anthropic.APIStatusError)
- [x] Test fixtures: newsdata, gnews, sec_edgar, rss response JSONs + RSS XML

> **Note:** `celery` package not yet installed in dev environment (no broker running).
> Celery tasks use fallback sync wrappers for test execution. Install `celery[redis]`
> and start Redis when flipping `USE_MOCK_DATA=false` for live ingestion.
> Load test (100 signals < 60s) deferred to when Redis is available.

#### Phase 3 Verification
```bash
# 101 tests pass (52 skipped = DB tests awaiting Supabase credentials)
pytest tests/ -q --tb=short
# 101 passed, 52 skipped

# Trigger manual ingest (when real API keys configured):
curl -X POST http://localhost:8000/api/v1/signals/ingest \
  -H "Authorization: Bearer {token}"
# After 30 seconds:
curl http://localhost:8000/api/v1/signals
# Returns ≥ 5 real classified signals
```

---

## Phase 4: AI Reasoning Layer

**Goal:** Given classified signals, the system predicts hiring opportunities, scores career fit, generates positioning advice, and creates action items — all automatically.

**Status:** ✅ COMPLETE

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 BE + 1 QA)

**Pre-requisite:** Phase 3 complete ✅

### Sprint 4.1 — Opportunity Predictor (Sessions 9–10)

**Agent: BE Opportunity Agent (1 agent)**

#### Tasks
- [x] `backend/app/agents/opportunity_predictor.py`
  - Input: company signals + user career profile
  - Output: predicted role, confidence (HIGH/MEDIUM/SPECULATIVE), timeline_weeks, why_it_fits, positioning_notes
  - Use Claude Sonnet with prompt caching on system prompt
  - Chain-of-thought reasoning: signals → company needs → role prediction
  - Prompt template must reference user's target roles and industries
- [x] `backend/app/agents/career_fit_scorer.py`
  - Input: predicted opportunity + user career profile embedding
  - Output: fit_score (0–100), fit_explanation, skill_gaps, strengths
  - Compare user embedding vs opportunity requirements (cosine similarity)
  - Claude Sonnet for nuanced fit reasoning
- [x] `backend/app/workers/predict_opportunities.py` (Celery)
  - `predict_for_company(user_id, company_id)` — runs after new signals
  - `score_opportunity_fit(user_id, opportunity_id)`
  - Triggered automatically after signal classification

**Agent: BE Action Generator Agent (1 agent)**

#### Tasks
- [x] `backend/app/agents/positioning_advisor.py`
  - Input: user profile + opportunity + company signals
  - Output: positioning narrative (2–3 paragraphs), key talking points, recommended approach angle
  - Claude Sonnet
- [x] `backend/app/agents/contact_identifier.py` — merged into opportunity_predictor per CLAUDE.md
  - ideal_contact_title is now output by OpportunityPredictorAgent directly
- [x] `backend/app/agents/action_generator.py`
  - Input: opportunity + fit score + contacts
  - Output: list of ActionItem objects (title, description, type, priority, due_date)
  - Priority scoring: urgency × confidence × fit_score
  - Claude Haiku (structured output generation)
- [x] `backend/app/workers/generate_actions.py` (Celery)
  - `generate_actions_for_opportunity(user_id, opportunity_id)`
  - `advise_positioning(user_id, opportunity_id)` — runs in parallel with fit scoring
  - `run_reasoning_pipeline(user_id, company_id)` — full Phase 4 pipeline entry point
  - Runs after opportunity is created + scored

**Agent: QA Reasoning Agent (1 agent)**

#### Tasks
- [x] Snapshot tests for all 4 agent prompts (67 tests, all passing)
  - test_opportunity_predictor_agent.py — 18 tests
  - test_career_fit_scorer_agent.py — 17 tests
  - test_positioning_advisor_agent.py — 14 tests
  - test_action_generator_agent.py — 18 tests
- [x] Test opportunity prediction: given funding signal → predicts VP-level role
- [x] Test fit scoring: MBA profile + strategy role → score ≥ 70
- [x] Test action generation: 1 opportunity → 2–4 actions with correct priority
- [ ] Verify Claude API costs: average cost per opportunity prediction < $0.10 (deferred — requires live API key)

#### Phase 4 Verification
```
1. Ingest signals for company "McKinsey"
2. Wait for Celery pipeline to complete
3. GET /opportunities → should show predicted opportunity
4. GET /actions → should show 2-4 action items for McKinsey
5. Each opportunity has: role, confidence, timeline, why_fit
```

---

## Phase 5: People Intelligence

**Goal:** Enrich companies and contacts via People Data Labs (PDL). User can search for key contacts at target companies. Email finding via Hunter.io.

**Status:** ✅ COMPLETE

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (1 BE + 1 QA)

**Pre-requisite:** Phase 4 complete ✅

### Sprint 5.1 — PDL + Hunter.io Integration (Session 11)

**Agent: BE Enrichment Agent (1 agent)**

#### Tasks
- [x] `backend/app/integrations/pdl_client.py`
  - People Data Labs REST API — replaces Proxycurl
  - `enrich_person(name, company, linkedin_url=None)` → contact profile
  - `enrich_company(name, domain=None)` → company profile + headcount
  - `search_people(company_name, title_keywords)` → list of matching contacts (sorted by seniority)
  - Free tier: 1,000 credits/month — 90-day Redis cache on ALL enriched profiles
  - Legally clean (public/open data only)
  - Error handling: 402 → None, 404 → None, network errors → None
- [x] `backend/app/integrations/hunter_client.py`
  - Hunter.io REST API — email finding by company domain + person name
  - `find_email(first_name, last_name, domain)` → EmailResult or None
  - `find_domain_emails(domain, limit=5)` → list sorted by confidence descending
  - Free tier: 25 searches/month — permanent Redis cache (1 year TTL)
  - 429/401/404 → None (never crashes the worker)
- [x] `backend/app/workers/enrich_contacts.py`
  - `enrich_company(company_id)` → PDL company enrichment
  - `enrich_contact(contact_id, priority)` → PDL person + Hunter.io email (high-priority only)
  - `find_key_contact(company_id, role_type)` → PDL search + auto-create contact record
  - `batch_enrich(contact_ids, priority)` → fan-out across contact list
  - Priority queue: high-fit contacts use "default" queue, others use "low"
- [x] `backend/app/api/v1/contacts.py` + `backend/app/services/contact_service.py`
  - `GET /contacts` — user's saved contacts (filterable by company_id)
  - `POST /contacts/search` — search PDL by company + title keywords
  - `GET /contacts/{id}` — contact detail (404 on not found)
  - Registered in router.py

**Agent: QA Enrichment Agent (1 agent)**

#### Tasks
- [x] Mock PDL API responses — mock mode via USE_MOCK_DATA flag (no credits used in tests)
- [x] Mock Hunter.io responses — same flag pattern
- [x] Test enrichment: company enriched with correct fields (headcount, industry)
- [x] Test contact search: returns ranked contacts by seniority (most senior first)
- [x] Test caching: second call with same input uses cache, not HTTP (test_pdl_client.py)
- [x] Test graceful degradation: PDL 402/404 → None, Hunter 429/401 → None
- [x] Integration tests: contacts API endpoints (50 tests total, all passing)
- [ ] Test quota tracking via agent_runs table (deferred — requires live DB)

---

## Phase 6: Frontend — Core Pages

**Goal:** Dashboard, Signals page, and Opportunities page fully functional with real API data. Mock data removed from these pages.

**Status:** ✅ COMPLETE

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 FE + 1 QA)

**Pre-requisite:** Phase 2 complete ✅ (can run in parallel with Phases 3–5)

### Sprint 6.1 — API Client & State Layer (Session 12)

**Agent: FE Foundation Agent (1 agent)**

#### Tasks
- [x] `frontend/lib/api/client.ts` — re-exports from lib/api with consistent import path
- [x] `frontend/hooks/useSignals.ts` — React Query v5 hook (list, single, ingest mutation)
- [x] `frontend/hooks/useOpportunities.ts` — React Query v5 hook (list, single, refresh mutation)
- [x] `frontend/hooks/useActions.ts` — React Query v5 hook (list, update, draft-email mutations)
- [x] `frontend/hooks/useProfile.ts` — React Query v5 hook
- [x] `frontend/hooks/useDashboardStats.ts` — React Query v5 hook
- [x] `frontend/components/shared/SkeletonCard.tsx` — animate-pulse skeleton loader
- [x] `frontend/components/shared/ErrorState.tsx` — error boundary with retry
- [x] `frontend/components/providers/QueryProvider.tsx` — React Query provider (wired in layout.tsx)
- [x] `frontend/types/index.ts` — already complete from Phase 2

### Sprint 6.2 — Dashboard & Signals Pages (Sessions 13–14)

**Agent: FE Page Agent A — Dashboard + Signals (1 agent)**

#### Tasks
- [x] `frontend/app/(dashboard)/page.tsx` — Dashboard wired to real API (no more mock imports)
  - useSignals / useOpportunities / useActions / useDashboardStats hooks
  - Skeleton loaders + ErrorState components
  - Auto-refresh every 5 minutes
- [x] `frontend/app/(dashboard)/signals/page.tsx` — Full signals page
  - Client-side filter (type multi-select, date range, company search, min relevance)
  - SignalCard list with selected state
  - SignalDetailPanel (Sheet slide-over)
  - "Ingest Now" button with loading/success feedback
- [x] `frontend/components/signals/SignalCard.tsx`
- [x] `frontend/components/signals/SignalFilters.tsx`
- [x] `frontend/components/signals/SignalDetailPanel.tsx`

**Agent: FE Page Agent B — Opportunities (1 agent)**

#### Tasks
- [x] `frontend/app/(dashboard)/opportunities/page.tsx`
  - Opportunity grid (1/2/3 columns responsive) with pagination ("Load more")
  - OpportunityFilters (confidence chips, status, timeline, sort)
  - OpportunityCard with fit_score progress bar
  - OpportunityDetail Dialog with all AI-generated fields
  - "Refresh Analysis" + "Create Action" buttons
- [x] `frontend/components/opportunities/OpportunityCard.tsx`
- [x] `frontend/components/opportunities/OpportunityDetail.tsx`
- [x] `frontend/components/opportunities/OpportunityFilters.tsx`

**Agent: QA FE Agent (1 agent)**

#### Tasks
- [x] Vitest tests: SignalCard (18 tests), SignalFilters (10 tests), OpportunityCard (11 tests), OpportunityDetail (11 tests)
- [x] Vitest hook tests: useSignals (7 tests), useOpportunities (7 tests)
- [x] Vitest page tests: Signals page (7 tests), Opportunities page (7 tests)
- [x] Playwright E2E: `e2e/phase6.spec.ts` — Dashboard, Signals, Opportunities golden paths + responsive
- **88/88 unit tests passing** ✅ (E2E require live server — run with `npx playwright test`)

---

## Phase 7: Frontend — Action Pages

**Goal:** Actions page, Outreach page, Profile page, and Settings page fully functional.

**Status:** ✅ COMPLETE — Sprint 7.1 ✅ | Sprint 7.2 ✅

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 FE + 1 QA)

**Pre-requisite:** Phase 6 complete ✅

### Sprint 7.1 — Actions & Outreach Pages (Sessions 15–16) ✅ COMPLETE

**Agent: FE Page Agent A — Actions (1 agent)**

#### Tasks
- [x] `frontend/app/(dashboard)/actions/page.tsx`
  - Kanban board view: Todo | In Progress | Done | Snoozed columns (click-to-move UX)
  - List view alternative (toggle button)
  - Filter: priority chips, type chips
  - Action card: title, company, priority badge, due date, type icon
  - Click → Action detail: full description, opportunity link, "Draft Email" button
  - Status update: Select dropdown in detail + quick-move button on card
  - Mark done / snooze actions
- [x] `frontend/components/actions/ActionKanban.tsx`
- [x] `frontend/components/actions/ActionCard.tsx`
- [x] `frontend/components/actions/ActionDetail.tsx`

**Agent: FE Page Agent B — Outreach + Profile + Settings (1 agent)**

#### Tasks
- [x] `frontend/app/(dashboard)/outreach/page.tsx`
  - Email draft list with tabs: All / Pending / Sent / Replied
  - Draft card: contact, subject, tone badge, status indicators
  - Email composer dialog: To field, subject, body textarea, tone selector, Generate/Send buttons
  - Sent tracking: opened/replied timestamps
- [x] `frontend/app/(dashboard)/profile/page.tsx`
  - Career profile form: current role, target roles (tag input), industries (tag input), aspirations textarea
  - Profile completeness progress bar
  - "Analyze Profile" button → AI re-analysis with run_id feedback
  - Save Profile with success/error feedback
- [x] `frontend/app/(dashboard)/settings/page.tsx`
  - API key status indicators (green checkmark / red X)
  - Signal source toggles (localStorage)
  - Notification preference toggles (localStorage)
  - Gmail OAuth connect flow + ingest frequency setting

### Sprint 7.2 — Analytics Page (Session 17) ✅ COMPLETE

**Agent: FE Analytics Agent (1 agent)**

#### Tasks
- [x] `frontend/app/(dashboard)/analytics/page.tsx`
  - Dashboard stats row: signals this week, new opportunities, actions completed, agent cost
  - Signal velocity AreaChart (recharts): 30-day view, stacked by type
  - Pipeline funnel: signals → opportunities → actions → outreach → replies (with conversion %)
  - Company distribution BarChart: top 10 companies by signal count
  - Agent cost table: agent name, calls, tokens, cost USD

#### QA (140 unit tests passing) ✅
- [x] ActionCard: 16 tests | ActionDetail: 13 tests
- [x] Actions page: 8 tests | Outreach page: 7 tests | Profile page: 8 tests
- [x] Playwright E2E: phase7.spec.ts (all 6 action pages)
- [x] Build: TypeScript clean, all 9 routes static ✅

> **Commit:** `da88f09 feat(phase-7): Frontend action pages — Actions, Outreach, Profile, Settings, Analytics`

---

## Phase 8: Email Automation

**Goal:** Users can generate AI-drafted emails and send them via Gmail with one click. Sent emails tracked.

**Status:** ✅ COMPLETE — 2026-04-13

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (1 BE + 1 FE + 1 QA)

**Pre-requisite:** Phases 5 + 7 complete ✅

### Sprint 8.1 — Gmail Integration (Sessions 18–19)

**Agent: BE Email Agent (1 agent)**

#### Tasks
- [x] `backend/app/integrations/gmail_client.py`
  - OAuth 2.0 flow: redirect URI, token exchange, refresh tokens
  - Store tokens encrypted in Supabase (per user)
  - `send_email(user_id, to_email, subject, body)` → returns gmail_message_id
  - `check_replies(user_id, message_ids[])` → returns reply status
- [x] `backend/app/agents/email_drafter.py`
  - Input: action + contact + opportunity + user_profile
  - Output: subject, body, tone, key_points_used
  - Claude Sonnet with prompt caching
  - 3 tone variants: Professional, Warm, Direct
  - Personalization: references specific signal that triggered the opportunity
- [x] `backend/app/api/v1/outreach.py`
  - `GET /outreach` — list drafts + sent
  - `POST /outreach/draft` — generate email draft
  - `POST /outreach/{id}/send` — send via Gmail
  - `POST /outreach/oauth/connect` — start Gmail OAuth
  - `GET /outreach/oauth/callback` — complete OAuth

**Agent: FE Email Agent (1 agent)**

#### Tasks
- [x] Wire outreach page to real API (already wired in page.tsx + api.ts — no changes needed)
- [x] Gmail OAuth connect flow (Settings page already calls outreachApi.connectGmail())
- [x] Real-time draft generation (loading state while AI generates — already implemented)
- [x] Send confirmation dialog (already implemented in ComposerDialog)
- [x] Success/failure toast notifications (already implemented)

**Agent: QA Email Agent (1 agent)**

#### Tasks
- [x] Test email draft generation with real Claude API (mock mode, 8 unit tests)
- [x] Mock Gmail API for send tests (8 unit tests in test_gmail_client.py)
- [x] Test OAuth token refresh flow (covered in GmailClient tests)
- [x] Test: drafts saved if user closes modal before sending (integration test)
- [x] E2E test: draft generated → reviewed → sent (8 integration tests in test_outreach_api.py)

---

## Phase 9: Full Integration & E2E

**Goal:** All systems talking to each other. Real data flows from signal ingestion → opportunities → actions → outreach. Remove ALL mock data from frontend.

**Status:** ✅ COMPLETE — 2026-04-14

**Superpowers Skills:** `/verification-before-completion`

**Pre-requisite:** Phases 6, 7, 8 complete ✅

### Sprint 9.1 — Integration (Sessions 20–22)

**Agent: Integration Agent (1 BE + 1 FE, working together)**

#### Tasks
- [x] Remove mock data fallbacks from frontend (PipelineViz, analytics page) ✅ 2026-04-13
- [x] Wire `GET /api/v1/analytics/dashboard` — return real stats ✅ 2026-04-13
- [x] Implement `GET /api/v1/analytics/dashboard` in backend ✅ 2026-04-13
- [x] Implement `GET /api/v1/agents/runs` + `GET /api/v1/agents/run-status/{id}` ✅ 2026-04-13
- [x] Verify: PipelineViz uses real data (shows zeros on load, real counts when API responds) ✅ 2026-04-13
- [x] Fix paginated response shape mismatches (signals/opportunities/actions: `data` array + `per_page`) ✅ 2026-04-13
- [x] Fix stale `app/page.tsx` overriding dashboard route — deleted boilerplate root page ✅ 2026-04-14
- [x] Fix all integration bugs (field name mismatches, routing conflict) ✅ 2026-04-14

**Agent: QA Integration Agent** ✅ COMPLETE 2026-04-14

#### Tasks
- [x] Playwright E2E tests for all 8 pages — 45 tests in `frontend/e2e/phase9.spec.ts` ✅ 2026-04-14
- [x] Test full user journey: Dashboard → Signals → Opportunities → Actions → Outreach → Analytics → Settings ✅ 2026-04-14
- [x] Performance: Dashboard <3s, Analytics <4s, Settings <3s — all pass ✅ 2026-04-14
- [x] No console errors check on all 8 pages ✅ 2026-04-14
- [x] Mobile (375px) and tablet (768px) responsive checks ✅ 2026-04-14
- [x] 253 backend tests passing, 0 failing ✅ 2026-04-14
- [x] Fix 8 stale integration tests (old field names) + add 11 new analytics/agents tests ✅ 2026-04-14

---

## Phase 10: Testing & Hardening

**Goal:** Production-ready code quality. 80%+ coverage. Security audit. Performance baseline.

**Status:** ✅ COMPLETE

**Pre-requisite:** Phase 9 complete ✅

### Sprint 10.1 — Coverage & Security (Sessions 23–25)

**Agent: QA Hardening Agent A (1 agent)**
- [x] Achieve 80% test coverage on all backend services
- [x] Achieve 70% test coverage on all frontend components
- [x] Fuzz test all API endpoints with invalid inputs
- [x] SQL injection: verify all queries are parameterized
- [x] XSS: verify all user content is escaped in frontend

**Agent: QA Hardening Agent B (1 agent)**
- [x] Rate limiting on all API endpoints (100 req/min per user)
- [x] API key exposure scan (no keys in git history)
- [x] Test Celery worker crash recovery
- [x] Test Redis connection loss recovery
- [x] Performance test: 100 signals classified in < 60 seconds

**Agent: QA Hardening Agent C (1 agent)**
- [x] Playwright visual regression tests (screenshots for all 8 pages)
- [x] Mobile responsiveness test (all pages on 375px)
- [x] Accessibility audit (axe-core on all pages)
- [x] Error boundary tests: API down → graceful error UI

---

## Phase 11: v1.0 Deployment

**Goal:** Apex running on a real server (or local with production config) for the primary user.

**Status:** ✅ COMPLETE — 2026-04-21

**Pre-requisite:** Phase 10 complete ✅

### Sprint 11.1 — Production Config (Sessions 26–27)

**Agent: BE Deployment Agent (1 agent)**

#### Tasks
- [x] Production `docker-compose.prod.yml`
  - FastAPI with Gunicorn workers ✅
  - Celery worker + beat scheduler ✅
  - Redis ✅
  - Nginx reverse proxy ✅
- [x] Environment separation: ENVIRONMENT flag (development/staging/production), ALLOWED_ORIGINS, JSON_LOGS
- [x] Database: `backend/scripts/run_migrations.sh` — applies all 12 migrations in order
- [x] Logging: structured JSON logs via `ApexJsonFormatter` (python-json-logger)
- [x] Health checks: `/health` returns environment + version + mock_mode; Docker healthcheck on backend
- [x] Create startup checklist in README

#### Phase 11 Verification
```
1. docker-compose -f docker-compose.prod.yml up
2. All services start without errors
3. POST /api/v1/signals/ingest works
4. Full pipeline runs end-to-end on prod Supabase
5. Frontend served via Nginx on port 80
```

---

## Phase 12: Live Production Run — Signal Classification Pipeline

**Goal:** All 1,446 real signals classified + embedded with real Claude Haiku + OpenAI calls. Opportunity Predictor running on relevant signals. Full end-to-end AI pipeline live.

**Status:** ✅ COMPLETE — 2026-04-23

**Pre-requisite:** Phase 11 complete ✅

### What Was Completed (Session 1 — 2026-04-21)

#### Signal Ingestion — FULLY LIVE ✅
- `ingest_signals.py`: `_get_companies_from_db()` queries 16 companies from Supabase
- `_run_newsdata` / `_run_gnews` / `_run_sec_edgar` now accept `company_name_map` so news APIs get readable names, DB writes get correct UUIDs
- `_persist_events`: fully rewritten with raw asyncpg, omits `embedding` column (pgvector-python not needed), dedup via SHA-256 hash
- `signal_service.py`: `trigger_ingest()` now dispatches real Celery tasks via `apply_async`
- **Result: 1,446 real signals in DB** from NewsData.io, GNews, SEC EDGAR (Form D + 8-K filings)
- **NOTE (discovered 2026-04-21):** All 1,446 signals were from GNews + SEC EDGAR only — NewsData.io produced 0 due to bugs fixed in Session 2 (see below)

#### Bug Fix — NewsData.io Silent Failure (Session 2 — 2026-04-21) ✅
**Root cause (two stacked bugs):**
1. `newsdata_client.py` was sending `from_date` in every request. The `/1/news` endpoint returns HTTP 422 `UnsupportedParameter` for this param — date filtering is a paid-only feature on `/1/archive`. Every call silently failed.
2. The empty `[]` result from the 422 error was being cached in Redis for 24h (`_cache_set` was called unconditionally). Every subsequent call returned the cached `[]` without hitting the API — explaining 0 hits on the NewsData.io portal.

**Fixes applied to `backend/app/integrations/newsdata_client.py`:**
- Removed `from_date` param from the request (the API returns recent news by default)
- `_cache_set` now only called when `articles` is non-empty (prevents caching error responses)
- Cache-hit check changed from `if cached is not None` → `if cached` (empty list no longer treated as a valid hit)
- Removed unused `timedelta` import

**Verified:** Direct API call without `from_date` returns HTTP 200 + 10 articles for "McKinsey".

#### Signal Classification — WIRED + RUNNING ✅
- `classify_signals.py`: live DB path fully wired
  - `_load_signal_from_db()`: asyncpg fetch of signal + company name + user career profile
  - `_update_signal_classification()`: asyncpg UPDATE of type/relevance_score/processed_at
  - `classify_signal` task calls real **Claude Haiku** for each signal
  - Gated-out signals (relevance < 0.4) also written to DB
- `embed_signal` task calls real **OpenAI text-embedding-3-small** (1536-dim vectors stored via `embedding=$1::vector`)
- `POST /signals/classify` endpoint added — queries unprocessed signals, dispatches batch task

### Sprint 12.2 — Pipeline Run ✅ COMPLETE (2026-04-23)

#### Task A: Signal Classification ✅ DONE
- Celery worker run with `--pool=threads --concurrency=4`
- ~450 signals classified with real Claude Haiku before pipeline advanced to next layer
- Remaining unclassified signals: left for Phase 14 re-run (Option B+C batch upgrade)

#### Task B: Opportunity Predictor ✅ DONE
- `OpportunityPredictorAgent` run on all signals with `relevance_score >= 0.4`
- Predicted opportunities saved to `opportunities` table in DB

#### Task C: Career Fit Scorer + Action Generator ✅ DONE
- `CareerFitScorerAgent` run on predicted opportunities → `fit_score` populated
- `ActionGeneratorAgent` run on opportunities → action items created in DB

---

## Phase 13: Signal & Agent Quality — MVP Hardening

**Goal:** Fix data quality issues discovered in Phase 12 live run. Raise Celery throughput. Rewrite agent prompts to be MBA-specific and output-grounded. No architecture changes, no new API costs.

**Status:** ✅ COMPLETE — Sprint 13.1 + 13.2 done 2026-04-22

**Prerequisite:** Phase 12 full pipeline run complete (all signals classified, opportunities predicted)

**Constraint:** No extended thinking, no new integrations, no significant LLM cost increase. Prompt caching on system prompts keeps cost flat.

---

### Sprint 13.1 — Data Pipeline Fixes ✅ COMPLETE (2026-04-22)

#### Task 1: SEC EDGAR — 90-day date filter ✅ DONE
**File:** `backend/app/integrations/sec_edgar_client.py`
- Added `EDGAR_LOOKBACK_DAYS = 90` constant
- Updated `fetch_form_d` and `fetch_8k_filings` defaults from `days_back=30` → `days_back=EDGAR_LOOKBACK_DAYS`
- **Acceptance:** Running `fetch_form_d("McKinsey")` returns only filings from last 90 days ✅

#### Task 2: NewsData.io — 0-article warning log ✅ DONE
**Files:** `newsdata_client.py`, `gnews_client.py`, `sec_edgar_client.py`
- All three sources now emit consistent structured warning on 0 results:
  ```
  logger.warning("Source %r returned 0 articles for company=%r — check key/quota/connectivity", source_name, company_name)
  ```
- newsdata: warning standardised to match format
- gnews: warning added after `articles` extraction
- sec_edgar: warning added in both `fetch_form_d` and `fetch_8k_filings`

#### Task 3: Celery — Raise concurrency to 4 (Windows-safe) ✅ DONE
**Decision:** Option A only for Phase 13. Option B+C (pre-filter + Sonnet batch) deferred to Phase 14.

- Changed `How to Restart` Step 3 from `--pool=solo` → `--pool=threads --concurrency=4`
- **Why:** Current 7s/signal × 1 worker = ~3 hours for 1,446 signals. Concurrency 4 brings this to ~45 minutes.
- **Test first:** Run 10 signals at concurrency 4 before bulk run to verify no race conditions on asyncpg connections
- **Acceptance:** Classification of 100 signals completes in under 12 minutes

---

### Sprint 13.2 — Agent Prompt Rewrites ✅ COMPLETE (2026-04-22)

**Constraint:** Prompt-only changes. No model swaps, no new tools, no architecture changes.

#### Task 4: Rewrite Signal Classifier Prompt ✅ DONE
**File:** `backend/app/agents/prompts/signal_classifier_v1.txt`
**Target:** Claude Haiku

- Added HEC Paris MBA framing with target sectors (Consulting, PE, Tech, FinServ) and role types
- 8 signal type definitions each with a concrete example article title
- 6-tier relevance scoring rubric calibrated to MBA business-building signals
- 3 full few-shot examples: HIGH (FUNDING/Mistral AI), MEDIUM (EXPANSION/Schneider), LOW (EARNINGS/Toyota)
- Do-not-classify rule: relevance_score 0.1 + fixed reasoning for short/context-free signals

#### Task 5: Rewrite Opportunity Predictor Prompt ✅ DONE
**File:** `backend/app/agents/prompts/opportunity_predictor_v1.txt`
**Target:** Claude Sonnet

- MBA role archetypes table: 8 archetypes mapped to signal types and seniority bands
- Strict confidence rules (HIGH requires 2+ signals ≥ 0.7 including FUNDING/MA/CONTRACT)
- Do-not-predict rule: single signal < 0.6 relevance → SPECULATIVE, full JSON still returned
- Specificity requirement with ✗/✓ examples enforcing concrete titles
- Citation requirement: `signal_citations: [{signal_id, key_quote}]` in every response
- Timeline guidance per signal type (FUNDING: 4–8w, MA: 8–16w, EXEC_HIRE: 4–6w, etc.)
- Aspiration alignment: conflicts with aspirations_text lower confidence by one level

#### Task 6: Rewrite Career Fit Scorer Prompt ✅ DONE
**File:** `backend/app/agents/prompts/career_fit_scorer_v1.txt`
**Target:** Claude Sonnet

- 4-dimension rubric: Industry Match + Role Level Fit + Skills Alignment + Aspiration Alignment (0–25 pts each)
- Anchor examples for absolute calibration: 95+ = lateral with upside, 75–85 = standard MBA, 55–65 = stretch, <30 = do not surface
- Skill gaps rule with ✗/✓ examples enforcing specificity ("no LBO/PE modelling" not "needs more experience")
- fit_explanation required to reference at least two dimensions by name

---

### Note: Agent Prompts V2 (Static) — ✅ SHIPPED 2026-04-26

> **What was done:** All 8 agent prompts (`signal_classifier`, `batch_signal_classifier`,
> `opportunity_predictor`, `career_fit_scorer`, `positioning_advisor`, `email_drafter`,
> `action_generator`, `profile_extractor`) rewritten as `_v2.txt` and the registry +
> per-agent `_load_system_prompt()` paths flipped from `_v1.txt` → `_v2.txt`.
> V1 files retained on disk for diff/rollback.
>
> **Improvements over V1:**
> - **Anthropic prompt-engineering patterns**: XML-tagged sections (`<role>`, `<inputs_you_receive>`,
>   `<reasoning_steps>`, `<output_schema>`, `<final_rules>`), explicit chain-of-thought reasoning
>   steps before output, anchor anti-pattern callouts (`✗ Bad / ✓ Good`).
> - **Full use of Phase 14/15 fields** in prompt instructions and few-shot examples:
>   `seniority_band`, `years_of_experience`, `work_history`, `key_achievements`,
>   `cover_letter_narratives`, `real_postings`.
> - **Stronger evidence requirements**:
>   - `opportunity_predictor` must cite each driving signal with `signal_id` + ≤15-word `key_quote`.
>   - `career_fit_scorer` must reference ≥2 dimensions by name AND cite a specific `work_history`
>     entry or `key_achievement`.
>   - `positioning_advisor` + `email_drafter` must cite at least one specific `key_achievement`.
> - **Phase 16 readiness**: `action_generator` v2 emits required `intended_effect` field.
> - **Profile extractor robustness**: whole-word seniority detection callout (avoids substring
>   false positives like "VP of Business Direction" matching DIRECTOR).
> - **Seniority gate alignment**: `opportunity_predictor` v2 explicitly forces SPECULATIVE when
>   the implied role is 2+ bands above user — pre-empts the post-prediction gate downgrade.

---

### Note: Agent Prompts V3 — Dynamic Prompt-Builder Layer (Required for v1.5 Multi-User)

> **Current state (v2):** Static `.txt` prompts. Persona context (HEC MBA, target sectors, role
> archetypes, scoring anchors, few-shot examples) is still baked into the prompt strings. The user's
> profile fields are passed in the user-message JSON, but the prompt's *frame* assumes an MBA
> consulting/PE/tech/finserv candidate.
>
> **The problem at v1.5:** When Apex expands to an MBA cohort or broader market, hardcoded
> persona breaks. A healthcare or public-sector user gets miscalibrated relevance scores,
> irrelevant role archetypes, and few-shot examples that point them away from their actual targets.
>
> **What V3 must do differently:**
> - Remove all hardcoded persona from the prompt body (sectors, role archetypes, scoring examples).
> - Inject ALL persona context dynamically from `career_profiles` at call time (target industries,
>   target roles, aspirations_text, seniority level, geography, persona archetype).
> - Per-agent persona context injected via a dedicated builder:
>   - **Signal classifier**: relevance scoring rubric derived from user profile, not baked in.
>   - **Opportunity predictor**: archetype table generated from user's target roles + industry, not fixed.
>   - **Career fit scorer**: dimension weights adjustable per user (e.g. geography weight higher
>     for users who flagged geography as a hard constraint).
>   - **Positioning advisor / email drafter**: tone-style library selectable from user preference.
>   - **Profile extractor**: seniority band rubric parameterised by industry (banking ≠ tech).
>
> **Architecture: prompt-builder layer.**
> - Replace static `prompt_path.read_text()` in each agent's `_load_system_prompt()` with a call to
>   a `PromptBuilder` class.
> - `PromptBuilder.build(agent_name, persona_context)` returns the assembled system prompt.
> - Prompt sources move from `prompts/*.txt` to `prompts/*.j2` (Jinja2) OR to a Python f-string
>   builder module per agent.
> - Each agent's input schema gains a `persona_context: PersonaContext` field (built once at
>   request time from the user's `career_profiles` row + preferences).
> - Few-shot examples either parameterised inside the template OR loaded from a per-user-archetype
>   library (e.g. `fixtures/few_shot/healthcare_director.json`).
> - System-prompt prompt-cache breakpoint moves to AFTER the persona-context block — so cache hits
>   are scoped per user, not globally. Acceptable trade-off; per-user cache hit rate is still high
>   because each user makes many calls in a session.
>
> **Migration path from V2 → V3:**
> 1. Keep V2 static files in place — they become the fallback / single-user template.
> 2. Build `PromptBuilder` infra + `PersonaContext` schema.
> 3. Convert prompts one agent at a time, starting with `opportunity_predictor` (highest impact)
>    and `career_fit_scorer` (most persona-sensitive scoring).
> 4. A/B test V2 vs V3 on existing single-user corpus — V3 must not regress quality on the
>    current user before rolling out.
> 5. Switch registry version to `3.0` per agent as it migrates.
>
> **Target version:** v1.5. Do not ship multi-user without this.
> **Prerequisite:** v1.0 stable (Phases 16–19 complete) before starting V3.

---

## Phase 14: Post-MVP Enhancements

**Goal:** Upgrade signal processing throughput, add real job market grounding to opportunities, build FE pipeline visibility, and make the codebase shareable/launchable.

**Status:** ✅ COMPLETE — 2026-04-25

**Prerequisite:** Phase 13 complete. Full pipeline has run end-to-end with quality prompts. MVP declared stable.

**Completed sprints:**
- Sprint 14.1 ✅ — Signal pre-filter (`SignalPreFilter`) + batch Sonnet classifier (`BatchSignalClassifierAgent`, 10 signals/call). `batch_classify_signals_upgrade` Celery task. `PRE_FILTER_ENABLED` + `BATCH_CLASSIFY_SIZE` config flags.
- Sprint 14.2 ✅ — Adzuna job board validation (`AdzunaClient` + `OpportunityValidatorService`). `real_postings JSONB` column on opportunities. FE "Real Posting Found" badge on `OpportunityCard`.
- Sprint 14.3 ✅ — FE Pipeline Progress Bar (`PipelineProgressBar` component, `usePipelineRun` hook). RunStatus schema enriched (stage/progress/ETA). Redis `report_stage()` helper. "Run Pipeline" button on Dashboard. `/pipeline/run` endpoint uses Celery task ID as `run_id`.
- Sprint 14.4 ✅ — Extended thinking enabled on `OpportunityPredictorAgent` (`thinking_budget=8000`). `base_agent._call_claude()` supports `thinking_budget` param; extracts text from content blocks.
- Sprint 14.5 ✅ — Launch package: `start.sh`, `.devcontainer/devcontainer.json`, `backend/app/db/seeds/seed_demo.py` (5 companies, 5 signals, 3 opps), `schema/initial.sql` (concatenated migrations), `QUICKSTART.md`.

**Key decisions / deviations:**
- asyncpg JSONB: pass Python `list` directly (not `json.dumps`) to prevent `InvalidTextRepresentationError`
- Celery task ID used as `run_id` returned to FE — progress Redis key linked to actual task
- `BATCH_CLASSIFY_SIZE` bounded with `Field(ge=1, le=10)` to prevent context overflow
- `positioning_notes` → `approach_angle` DB column rename deferred to Phase 15 (noted in technical debt)

---

### Sprint 14.1 — Signal Processing Upgrade (Option B+C Combo)

**Decision:** Pre-filter first (Option C), then batch with Sonnet (Option B). Confirmed 2026-04-21.

- **Step 1 — Keyword pre-filter:** Before any AI call, run a fast keyword + company-name relevance check. Signals matching none of the user's target industries, companies, or signal keywords get `relevance_score: 0.05` and skip the AI gate. Target: eliminate ~40–60% of signals before Haiku/Sonnet.
- **Step 2 — Sonnet batch classifier:** Replace Haiku 1-signal/call with Sonnet at 10 signals/call. Confirmed sweet spot at 10 (attention starts diluting above that).
- **Expected outcome:** 3-hour bulk classification → under 10 minutes. Cost: ~$2.50 for 1,446 signals vs ~$0.65 currently — acceptable.
- **Note:** When re-evaluating, also consider whether the prompt rewrite from Phase 13 + Haiku is already good enough before committing to Sonnet.

### Sprint 14.2 — Real Opportunity Grounding (Job Board Layer)

**Decision:** Add Adzuna API (free, no rate limit abuse, 10M+ postings) as a validation layer. Confirmed 2026-04-21.

- **Architecture shift:** Opportunity Predictor output becomes "prediction + validation". After predicting a role, the system searches Adzuna for matching open roles at that company or peer companies.
- **Output enrichment:** Opportunity record gains `real_postings: [{title, url, company, posted_date}]` — "We predicted Head of Strategy; here are 3 open roles matching that at this company right now."
- **Fallback:** If no real posting found, opportunity is labelled PREDICTED (speculative). If a real posting is found, it upgrades to VALIDATED.
- **FE:** Opportunity cards show a "Real Posting" badge when validated.

### Sprint 14.3 — FE Pipeline Progress Bar

**Decision:** Polling-based (Option A), Supabase Realtime upgrade in v1.5. Confirmed 2026-04-21.

- Add "Run Pipeline" button to Dashboard
- Pipeline stages displayed: `[Ingest] → [Classify] → [Predict] → [Fit Score] → [Actions]`
- Each stage shows: status chip (queued/running/done/error) + count (e.g. "847/1446")
- FE polls `GET /agents/run-status/{run_id}` every 2s
- Backend returns `{stage, completed, total, status, eta_seconds}`
- Time estimate shown: "~18 minutes remaining"

### Sprint 14.4 — Extended Thinking for Opportunity Predictor

**Decision:** Deferred from Phase 13 (MVP constraint). Enable in Phase 14 when MVP is locked. Confirmed 2026-04-21.

- Enable `thinking` with `budget_tokens: 8000` on `OpportunityPredictorAgent`
- Measure: opportunity quality score (human review), not just output format
- Cost impact: ~3x token cost on Opportunity Predictor calls — acceptable given low call volume (1 per company per run)

### Sprint 14.5 — Shareable / Launch Package

**Decision:** Docker Compose foundation (Phase 11) is 90% there. Add setup script + QUICKSTART. Confirmed 2026-04-21.

- `start.sh`: checks Docker installed, copies `.env.example` → `.env`, prompts for API keys, runs `docker-compose up --build`, seeds demo companies
- `QUICKSTART.md`: step-by-step for a technical tester with zero codebase context
- `.devcontainer/devcontainer.json`: GitHub Codespaces one-click support (for non-local testers)
- Demo seed data: 5 companies + 20 signals + 3 opportunities pre-loaded so first-time experience is non-empty

---

## Phase 15: Resume & Document Intelligence

**Goal:** Users upload their resume and cover letters. A Profile Extractor Agent parses them into structured career data, enriching all downstream agents with real experience, seniority, achievements, and positioning narratives.

**Status:** ✅ COMPLETE — 2026-04-26

**Prerequisite:** Phase 14 complete. ✅

**What was built:**
- DB migrations 015 (`user_documents`), 016 (career_profiles Phase 15 columns), 017 (`positioning_notes` → `approach_angle` rename)
- `DocumentExtractor` service (pdfplumber + python-docx, async-safe via `run_in_executor`)
- `DocumentService` + full document CRUD API (`POST /profile/documents`, `GET`, `DELETE`, `POST /analyze`, `GET /pending-review`, `POST /approve`)
- `ProfileExtractorAgent` (Claude Sonnet) — extracts `years_of_experience`, `seniority_band`, `work_history`, `key_achievements`, `cover_letter_narratives`
- Celery `extract_profile` worker with staging JSON approval flow
- `SeniorityGate` utility — maps role title → seniority band; downgrades confidence if predicted role is 2+ bands above user
- Signal Classifier enriched: `user_seniority_band` + `user_work_history_companies` in input
- Opportunity Predictor enriched: `seniority_band`, `years_of_experience`, `work_history_summary` in input
- Career Fit Scorer enriched: `work_history`, `key_achievements` in user profile input
- Positioning Advisor enriched: `cover_letter_narratives` (target-context matched), `key_achievements`
- Email Drafter enriched: `key_achievements`, `cover_letter_narratives` (target-context matched)
- Frontend: `DocumentUploadSection` component (upload, label, delete, analyze trigger)
- Frontend: `ExtractionReviewPanel` component (staged profile display + approve button)
- `StagedProfile` shared type in `frontend/types/index.ts`
- 104 unit tests, 0 failures

---

### Sprint 15.1 — Document Upload & Storage ✅

**Backend:**
- Add `user_documents` table migration (see CLAUDE.md Section 4 for schema)
- Add Supabase Storage bucket `user-documents` (private, user-scoped RLS)
- `POST /profile/documents` — accepts multipart/form-data (PDF or DOCX, max 10MB)
  - Validates file type (reject anything that isn't PDF/DOCX)
  - Stores file to Supabase Storage, writes metadata row to `user_documents`
  - Returns `{doc_id, filename, doc_type, extraction_status: "PENDING"}`
- `GET /profile/documents` — list all user documents + extraction status
- `DELETE /profile/documents/{id}` — remove file from Storage + DB row
- Local text extraction runs synchronously on upload (pdfplumber for PDF, python-docx for DOCX)
  - Extracted text written to `user_documents.extracted_text`
  - Status updated: `PENDING` → `EXTRACTED`

**Frontend (Profile page):**
- New "Documents" section above the existing form
- Drag-and-drop upload zone accepting PDF/DOCX
- User labels each upload: RESUME or COVER LETTER (dropdown)
- Cover letter: text input for `target_context` ("PE firms", "tech startups", "consulting")
- Document list: filename, type badge, target_context, date, delete button
- Profile completion bar: +20% per document uploaded (max 2 documents for full credit)

**Tests:**
- Unit: file type validation, text extraction from fixture PDFs/DOCXs
- Integration: upload → Storage → DB row → GET list

---

### Sprint 15.2 — Profile Extractor Agent ✅

**New agent:** `backend/app/agents/profile_extractor.py`

**Model:** Claude Sonnet (one-time cost ~$0.04/user for resume + 2 cover letters)

**Input:**
```json
{
  "user_id": "...",
  "resume_text": "...",
  "cover_letters": [
    {"text": "...", "target_context": "PE firms"},
    {"text": "...", "target_context": "tech startups"}
  ],
  "existing_profile": {"current_role": "...", "target_roles": [...]}
}
```

**Output:**
```json
{
  "years_of_experience": 6,
  "seniority_band": "ASSOCIATE",
  "education": [{"degree": "MBA", "institution": "HEC Paris", "year": 2026, "field": "General Management"}],
  "work_history": [{"company": "BCG", "title": "Senior Consultant", "start_year": 2021, "end_year": 2024, "summary": "..."}],
  "key_achievements": [{"achievement": "...", "impact": "...", "context": "..."}],
  "inferred_skills": ["financial modelling", "stakeholder management"],
  "cover_letter_narratives": [{"target_context": "PE firms", "core_narrative": "..."}]
}
```

**Trigger:** `POST /profile/documents/{id}/analyze` → dispatches Celery task → returns `{run_id}`
- Runs after all documents are uploaded (user clicks "Analyze my profile")
- OR auto-triggered after first document upload

**Approval flow:**
- Extraction output stored in a staging area (not yet written to `career_profiles`)
- `GET /profile/documents/pending-review` returns extracted fields for user review
- `POST /profile/documents/{id}/approve` — user approves extracted fields
  - Writes approved fields to `career_profiles`
  - Sets `profile_source = RESUME` (or `BOTH` if manual fields also present)
  - Sets `last_analyzed_at = now()`
  - Clears staging area
- User can edit any field before approving

**Tests:**
- Unit: prompt output parsing, Pydantic validation
- Integration: upload + extract + approve flow end-to-end
- Snapshot: fixture PDF → known extraction output

---

### Sprint 15.3 — Wire Enriched Profile to All Agents ✅

Update all agent input schemas and prompts to consume the new profile fields:

**Signal Classifier:**
- Add `seniority_band` and `work_history_industries[]` to `UserProfileSummary`
- Prompt update: relevance scoring now considers user's actual industry background, not just aspirations

**Opportunity Predictor:**
- Add `years_of_experience`, `seniority_band`, `work_history` to `UserProfileSummary`
- Prompt update: seniority-appropriate role prediction with explicit anchor examples
- **Hard seniority gate** (code-level, post-prediction):
  - Parse predicted role title for seniority keywords (Chief/C-Suite/VP/Director/Manager/Lead/Senior/Associate/Analyst)
  - If predicted band > user band by 2+ levels → force `confidence = SPECULATIVE`
  - Log the downgrade for debugging

**Career Fit Scorer:**
- Add `work_history`, `key_achievements` to `UserProfileForScoring`
- Prompt update: "Role Level Fit" dimension now has explicit experience evidence to cite

**Positioning Advisor:**
- Add `cover_letter_narratives` (matching target company's industry) to input
- Prompt update: reference specific achievements and cover letter narrative in positioning

**Email Drafter:**
- Add `key_achievements`, `cover_letter_narratives` (target-context matched) to user_profile input
- Prompt update: reference at least one specific achievement in every email draft

**Tests:**
- Integration: full pipeline run with enriched profile → verify opportunities are seniority-appropriate
- Unit: seniority gate logic for all band combinations

---

### Sprint 15.4 — Seniority Gate & FE Profile Review UI ✅

**Seniority gate** (already described in Sprint 15.3 — implement here alongside FE):
- `SeniorityGate` utility class: maps role title keywords → `seniority_band` enum
- Called in `predict_opportunities` worker after `OpportunityPredictorAgent.predict()`
- Returns `(original_confidence, gated_confidence, reason)` for audit trail

**Frontend — Profile extraction review UI:**
- After "Analyze" completes, Profile page shows a review panel: extracted fields side-by-side with current manual entries
- User toggles each field: "Use extracted" vs "Keep existing"
- Single "Apply approved fields" button writes all toggled-on fields
- Confirmation toast: "Profile updated — re-scoring 3 existing opportunities..."
- Existing opportunities get async re-score triggered in background

---

## Phase 16: Action Page Revamp

**Goal:** Actions show full context — which job, which signal triggered it, what the action is expected to achieve. Company filter added. Users trust the system because they understand the reasoning.

**Status:** 🔲 NOT STARTED

**Prerequisite:** Phase 14 complete. Phase 15 Sprint 15.3 recommended (richer profile = better intended_effect).

---

### Sprint 16.1 — Backend Data Enrichment

**DB migration:**
- Add `intended_effect text` column to `actions` table

**Action Generator prompt update:**
- Add `intended_effect` to output schema: 1 sentence on what this action achieves
- Example: `"Opening a warm referral path before the role is posted publicly."`
- Required field — Action Generator must always output it

**`GET /actions` API update:**
- Add `company_id` query param as filter (alongside existing `status`, `priority`)
- JOIN `opportunities` table: include `predicted_role`, `confidence`, `fit_score`
- JOIN `signals` table (via `source_signal_id`): include signal `title`, `type`
- Response enriched with: `opportunity_role`, `opportunity_confidence`, `source_signal_title`, `source_signal_type`, `intended_effect`

**`GET /actions/{id}` new endpoint:**
- Full action detail: all fields + full opportunity detail + full signal detail

**Tests:**
- Unit: enriched query returns correct JOIN data
- Integration: action list + detail with real DB data
- Confirm `company_id` filter works correctly

---

### Sprint 16.2 — Frontend Action Page Redesign

**Company filter bar:**
- Horizontal chip bar above the action list: "All" | "McKinsey" | "BCG" | "Bain" ...
- Chips generated from distinct `company` values in the action list
- Selecting a chip filters the list client-side (fast, no extra API call)

**Action cards (redesigned):**
```
┌──────────────────────────────────────────────────────┐
│ [HIGH] Connect with Sarah Chen · McKinsey             │
│                                                       │
│ For: Strategy Manager (HIGH confidence, fit 87/100)   │
│ Signal: "McKinsey hired 3 ex-Bain partners in Paris"  │
│ Why this action: Opening a warm referral path before  │
│                  the role is posted publicly.         │
│                                                       │
│ Due: 28 Apr  [TODO ▾]  [Draft outreach]              │
└──────────────────────────────────────────────────────┘
```

**Empty state:** "No actions yet. Run the pipeline to generate opportunities and actions."

**Tests:**
- Playwright: company filter, action card content, status change, draft email trigger

---

## Phase 17: Outreach Expansion

**Goal:** Users can reach contacts via LinkedIn (message text, copy/paste) or email. LinkedIn message generation available even without Gmail connected. PDL contact LinkedIn URLs surfaced.

**Status:** 🔲 NOT STARTED

**Prerequisite:** Phase 16 complete (action detail context feeds Email Drafter).

---

### Sprint 17.1 — LinkedIn Message Generation

**Email Drafter prompt update:**
- Add `channel` input field: `EMAIL | LINKEDIN`
- For `LINKEDIN`:
  - Connection note variant: max 300 chars (LinkedIn connection request limit)
  - InMail variant: max 2000 chars (LinkedIn InMail limit)
  - Both reference specific achievement + role + company context
  - Cover letter narrative for matching `target_context` injected automatically

**`POST /outreach/draft` API update:**
- Add `channel: str = "EMAIL"` to `DraftEmailRequest`
- For `LINKEDIN` channel: no Gmail integration required — returns message text directly
- Response includes `linkedin_profile_url` from contact PDL enrichment data

**DB migration:**
- Add `channel text DEFAULT 'EMAIL'` to `outreach_emails` table
- LINKEDIN drafts stored as `outreach_emails` with `channel='LINKEDIN'` (no `gmail_message_id`)

**Tests:**
- Unit: LinkedIn character limit validation (300 / 2000)
- Integration: draft LinkedIn message end-to-end

---

### Sprint 17.2 — PDL LinkedIn URL + FE Channel Routing

**PDL contact enrichment already returns `linkedin_url`** — surface it everywhere:
- `GET /contacts/{id}` response includes `linkedin_url`
- `GET /actions` enriched response includes `contact_linkedin_url`

**Frontend updates:**
- Action cards: LinkedIn icon button next to "Draft outreach" → opens LinkedIn profile in new tab
- Outreach draft modal: toggle at the top: `[✉ Email]  [in LinkedIn]`
  - Switching channel re-drafts with appropriate character limits
- LINKEDIN draft view: two text areas (Connection Note + InMail) + "Copy" buttons for each
- No "Send" button for LinkedIn (copy/paste flow — no API)
- GMAIL not connected banner: "Gmail not connected — use LinkedIn outreach or connect Gmail in Settings"

**Tests:**
- Playwright: channel toggle, copy buttons, LinkedIn URL click-through
- Unit: outreach list filter by channel

---

## Phase 17B: Target Company Intelligence

**Goal:** Users can curate their own list of target companies in the Profile page. A new "Target Companies" section lets users add companies manually or via AI-powered "Find Similar" recommendations based on their profile and existing target list.

**Status:** 🔲 NOT STARTED

**Prerequisite:** Phase 15 complete (career profile extraction gives the profile context needed for AI similarity matching).

---

### Sprint 17B.1 — Target Companies Backend

**Schema change:**
- Add `target_company_ids uuid[]` to `career_profiles` — list of company UUIDs the user has explicitly targeted
- Add `POST /profile/target-companies` — add a company (by name or ID)
- Add `DELETE /profile/target-companies/{company_id}` — remove a company
- Add `GET /profile/target-companies` — list with company details (name, industry, domain, enrichment status)
- When a company is added: upsert into `companies` table, then ensure it's in the next pipeline run's company scope

**Pipeline scope change:**
- `ingest_signals.py`: prioritize `target_company_ids` companies in signal ingestion (run them first, always include them)
- Ensure target companies are included in `_fetch_companies_with_relevant_signals` even if they have <3 signals

**Tests:**
- Unit: target company upsert creates company row + updates career_profile.target_company_ids
- Integration: pipeline includes explicitly targeted company even with 0 signals

---

### Sprint 17B.2 — Target Companies Frontend

**Profile page — new "Target Companies" section:**
- Display current target companies as cards (company name, industry, signal count)
- Search field: type company name → debounced search against `GET /companies?q=name` (existing endpoint)
- "Add" button → calls `POST /profile/target-companies`
- Remove button on each card → calls `DELETE /profile/target-companies/{id}`
- Empty state: "Add companies you want to work at — they'll be prioritized in your pipeline"

**Tests:**
- Unit: `TargetCompanyCard` renders with name + signal count + remove button
- Integration: add flow shows company in list; remove flow removes it

---

### Sprint 17B.3 — AI "Find Similar Companies" Feature

**UI:** "Find 10 More Like These" button appears when user has ≥1 target company. Calls:
- `POST /profile/target-companies/suggest` → returns `[{name, domain, industry, why_similar}]`

**Backend — new endpoint:**
- Reads user's current target companies + career profile
- Calls Claude Sonnet with: user profile (seniority, industries, aspirations, target role types) + current company names + industries
- Claude outputs 10 company suggestions with: `name`, `domain`, `industry`, `why_similar` (1 sentence)
- Returns suggestions as a list — user sees each with a ✓ (add) / ✗ (skip) toggle
- On confirm: calls `POST /profile/target-companies` for each approved suggestion

**Agent:** No new agent needed — inline Claude call from the endpoint (not a Celery task; ~2s response acceptable)

**Constraints:**
- Suggestions must not include companies already in target list
- Suggestions must be real companies (Claude instructed to only name verifiable companies)
- No hallucinated domains — domain field is optional; verification is downstream task

**Tests:**
- Unit: suggestion response schema validation (name, industry, why_similar required)
- Integration: mock Claude call returns 10 suggestions; endpoint returns them correctly

---

## Phase 18: Signal Quality & Entity Disambiguation

**Goal:** Reduce signal noise by ensuring search queries are company-specific and pre-filter checks entity context before classifying. Eliminate "Usain Bolt wins race" type noise.

**Status:** 🔲 NOT STARTED

**Prerequisite:** Phase 14 Sprint 14.1 (keyword pre-filter) complete — Phase 18 extends it.

---

### Sprint 18.1 — Domain-Qualified Search Queries

**Problem:** Searching "Bolt" returns Usain Bolt articles. "Apple" returns apple fruit articles.

**Fix — `ingest_signals.py` + NewsData/GNews clients:**
- Build a `search_query` per company using: `company name + industry + optional HQ city`
  - Example: `"Bolt electric scooter mobility"` not just `"Bolt"`
  - Example: `"Apple technology computing"` not just `"Apple"`
- `companies` table already has `industry` field — use it
- Add `search_alias` optional field to companies (e.g. "Bolt Mobility" for the Bolt scooter company)
  - Editable via `PUT /companies/{id}` + Settings UI
- NewsData client: use `q` param with multi-term query (already supports boolean-ish)
- GNews client: use `q` with quoted phrase for company name + industry term

**Tests:**
- Unit: `build_search_query(company_name, industry, hq_city)` returns qualified string
- Integration: mock API calls verify qualified query is sent, not bare name

---

### Sprint 18.2 — Pre-Filter Entity Context Check

**Extends Phase 14.1 keyword pre-filter with entity validation step:**

Before passing a signal to the classifier, check that the signal is actually about the target company:
- **Check 1:** Company name appears in title or description (already implicit from search, but some results slip through)
- **Check 2:** At least one of the following also appears: company domain keyword, industry term, HQ city, known product name
- **Implementation:** Fast regex check in `classify_signals.py` pre-filter step
  - `CompanyContextMatcher` class: takes company dict, builds term set, checks against signal text
  - If 0 terms match → `relevance_score = 0.05`, skip AI classification, log as "entity_mismatch"
- **Company term set sources:** `companies.domain` (extract root word), `companies.industry`, `companies.location`

**Monitoring:**
- Log count of entity_mismatch per company per run
- If a company has >50% entity_mismatch rate → flag in logs for `search_alias` review

**Tests:**
- Unit: `CompanyContextMatcher` with Bolt (expected: blocks Usain Bolt), Apple (expected: passes Apple tech)
- Integration: full classify run shows reduced noise signals for ambiguous company names

---

## Phase 19: Analytics Real Data + Historical Backtesting

**Goal:** Analytics page shows real data from the DB. Backtesting framework validates that historical signals would have predicted actual job postings.

**Status:** 🔲 NOT STARTED

**Prerequisite:** Phase 14 Sprint 14.2 (Adzuna job board layer) must be complete for backtesting.

---

### Sprint 19.1 — Wire Analytics FE to Real Backend

**Backend `GET /analytics/dashboard`** (already exists — verify it returns):
- `signals_this_week: int` — signals ingested in last 7 days
- `new_opportunities: int` — opportunities created in last 7 days
- `actions_completed: int` — actions with status=DONE in last 7 days
- `outreach_sent: int` — emails/LinkedIn messages sent in last 7 days
- `pipeline_health: {classified_pct, predicted_pct, actioned_pct}` — funnel percentages
- `top_companies: [{name, signal_count, opportunity_count}]` — top 5 by activity

**Frontend:**
- Replace all mock data references in `analytics/page.tsx` with real `GET /analytics/dashboard` calls
- Add loading skeleton + error boundary
- Pipeline funnel: Signals → Classified → Opportunities → Actions → Outreach (real %)
- "Top companies by activity" bar chart (real data)
- Signal type breakdown pie chart (FUNDING / EXEC_HIRE / EXPANSION / etc.)

**Tests:**
- Unit: analytics endpoint returns correct counts from fixture DB
- E2E Playwright: analytics page loads real data, no mock fallback visible

---

### Sprint 19.2 — Historical Backtesting Framework

**Concept:** Fetch signals from 60–90 days ago → run pipeline → compare predicted roles against actual Adzuna job postings from that period.

**Implementation:**
- `POST /backtest/run` — accepts `{lookback_days: int, company_ids: []}` → enqueues Celery task
  - Fetches signals dated `now() - lookback_days` from existing DB (no new API calls)
  - Runs Opportunity Predictor on those signals
  - Queries Adzuna for postings at those companies in the same period
  - Compares: did we predict a role that was posted within 8 weeks?
- `GET /backtest/results/{run_id}` — returns comparison table:
  ```json
  {
    "hit_rate": 0.67,
    "predictions": [
      {"company": "McKinsey", "predicted_role": "Strategy Manager",
       "adzuna_match": "Senior Strategy Consultant", "match_score": 0.82}
    ]
  }
  ```
- Results stored in `backtest_runs` table for historical comparison

**FE (Analytics page, new tab "Backtesting"):**
- "Run Backtest" button → shows progress → results table
- Hit rate badge: "67% of predictions matched real postings within 8 weeks"

**Tests:**
- Unit: role similarity matching (predicted vs actual title)
- Integration: backtest run with fixture historical signals + mock Adzuna data

---

## Phase 20: Self-Host Foundations

**Goal:** Make the codebase safe to clone, deploy, and operate by someone who is not Swapneet.

**Status:** 🔲 NOT STARTED

**Design reference:** `docs/superpowers/specs/2026-04-24-multi-user-self-host-design.md`

---

### Sprint 20.1 — Consolidated Schema + Bootstrap Script

**Deliverables:**
- `schema/initial.sql` — single file that creates ALL tables, RLS policies, `pgvector` extension, indexes, and seed reference data from an empty Supabase project. Must be idempotent-within-a-single-run (wrapped in `DO $$ ... $$` blocks where needed).
- Tested: paste into a fresh Supabase project → app boots → basic flows work (login, signal list, ingestion trigger)
- `scripts/bootstrap_owner.py` — reads `OWNER_EMAIL` + `OWNER_PASSWORD` from env, creates one Supabase Auth user via the service-role key, inserts matching `users` row
- Backend startup hook: if no owner exists, log clear instructions (`Run: python scripts/bootstrap_owner.py`) and refuse to serve authenticated endpoints

**Tests:**
- Integration: run `initial.sql` against a test Supabase project, assert all expected tables/policies/indexes exist
- Unit: bootstrap script is idempotent (running twice doesn't create duplicates)

---

### Sprint 20.2 — Hardcode Audit + SaaS-Pivot Readiness

**Deliverables:**
- Grep audit report: zero hardcoded user IDs, user names, HEC-specific strings, or absolute filesystem paths in any non-prompt code path. Prompt templates may reference the MBA persona (that's intentional for v1.0 — see v1.5 deferral note).
- Config audit: every API key, URL, feature flag, and dev-only value reads from environment variables. `.env.example` lists every variable with a comment describing what it does.
- SaaS-pivot readiness checklist (documented in `docs/saas-pivot-readiness.md`):
  - ✅ All queries `user_id`-scoped
  - ✅ RLS policies enforce isolation
  - ✅ `agent_runs` writes on every agent call (cost metering precondition)
  - ✅ `MOCK_AGENTS` and `USE_MOCK_DATA` gate all dev-only paths
  - ✅ Supabase public-signup toggle is the only switch needed to enable multi-user install
- Remove `login.json`, any committed test fixtures containing real credentials

**Tests:**
- CI job that greps for common leak patterns (hardcoded emails, absolute Windows paths `E:\`, `localhost` in non-dev files)

---

## Phase 21: Railway Deploy Template

**Goal:** "Deploy on Railway" button in README works end-to-end from a fresh fork with no manual steps beyond pasting env vars.

**Status:** 🔲 NOT STARTED

**Depends on:** Phase 20 complete.

---

### Sprint 21.1 — Railway Service Configuration

**Deliverables:**
- `railway.json` defining four services: `backend` (web), `celery-worker`, `redis` (managed), `frontend`
- Per-service build command, start command, health check endpoint, resource limits
- Service-to-service URL wiring: backend reads `REDIS_URL` from Railway's managed Redis; frontend reads `NEXT_PUBLIC_API_URL` from backend's public Railway domain
- `railway-env.md` listing every env var Railway needs, grouped by integration, with per-variable "where to get this" notes and links to `API-KEYS.md`
- "Deploy on Railway" markdown button snippet ready for README (Phase 24 inserts it)

---

### Sprint 21.2 — End-to-End Deploy Smoke Test

**Deliverables:**
- From a completely fresh fork: click deploy → authenticate with Railway → paste env vars from a prepared test set → wait for build → all four services running green
- Frontend loads, login works, signal ingestion can be triggered, Celery worker consumes the job, Redis is reachable
- Documented gotchas (cold-start time, any manual post-deploy steps) in `railway-notes.md`

**Tests:**
- Manual end-to-end: run the full flow at least once from scratch; note time-to-first-successful-login
- Automated: Playwright smoke test that runs against a Railway preview deployment (optional stretch goal)

---

## Phase 22: First-Run Setup Experience

**Goal:** A newly-deployed install tells the user exactly what's missing and how to fix it, without requiring them to read documentation first.

**Status:** 🔲 NOT STARTED

**Depends on:** Phase 20 complete. Runs in parallel with Phase 21.

---

### Sprint 22.1 — System Status Endpoint

**Deliverables:**
- `GET /api/v1/system/status` — authenticated owner-only endpoint returning per-integration health:
  ```json
  {
    "anthropic":  {"status": "ok"},
    "openai":     {"status": "ok"},
    "newsdata":   {"status": "missing_key"},
    "gnews":      {"status": "invalid_key", "error": "HTTP 403: ..."},
    "pdl":        {"status": "ok"},
    "hunter":     {"status": "unreachable", "error": "connection timeout"},
    "supabase":   {"status": "ok"},
    "gmail_oauth":{"status": "not_configured"}
  }
  ```
- Each integration test is a lightweight call (Anthropic `list_models`, NewsData 1-article fetch, etc.) cached for 60 seconds to avoid repeated calls
- Clear error messages in `error` field so user can paste directly into Claude for troubleshooting

**Tests:**
- Unit: status for each integration when key missing / invalid / ok
- Integration: endpoint returns expected shape; caching works

---

### Sprint 22.2 — `/setup` Wizard Frontend

**Deliverables:**
- First-login detection: if `/system/status` reports any `missing_key` or `invalid_key` for critical integrations, redirect to `/setup` instead of `/dashboard`
- `/setup` page: one card per integration with (a) what the key does, (b) link to signup page, (c) instructions to paste into Railway's env var UI with a screenshot, (d) "Re-check" button that re-runs `/system/status`
- Visual progress: checked-off integrations show green, remaining show amber, "You're all set" state when everything is ok
- Skip-and-continue option for non-critical integrations (Gmail OAuth, Hunter) — user can wire them later

**Tests:**
- Playwright: simulate missing keys → wizard renders → adding a key and re-checking updates the state → all-green redirects to Dashboard

---

## Phase 23: Non-Technical User Documentation

**Goal:** A first-time user with no CS background can deploy and start using Apex from the README in under 45 minutes.

**Status:** 🔲 NOT STARTED

**Depends on:** Phases 21 + 22 complete (need real deploy + wizard to screenshot).

---

### Sprint 23.1 — Core Installation Docs

**Deliverables:**
- `QUICKSTART.md` rewritten with step-by-step instructions and screenshots for:
  1. Supabase signup (screenshot the signup page)
  2. Creating a new Supabase project (screenshot)
  3. Pasting `schema/initial.sql` into the SQL Editor (screenshot)
  4. Copying Supabase URL + keys from the dashboard (screenshot)
  5. Signing up for each API key (Anthropic, OpenAI, NewsData, GNews, PDL, Hunter) — one section each
  6. Clicking the "Deploy on Railway" button (screenshot)
  7. Pasting env vars into Railway's UI (screenshot)
  8. Waiting for build + first login
  9. Using the in-app setup wizard if anything is missing
- `API-KEYS.md` with per-provider signup flow + "where to find the key" screenshots

---

### Sprint 23.2 — Supporting Docs

**Deliverables:**
- `TROUBLESHOOTING.md` with common errors and fixes, plus the "paste the error into Claude" pattern documented explicitly
- `LICENSE` — MIT
- `CONTRIBUTING.md` — how to fork, PR conventions, testing requirements (light touch, no heavy process)
- `SECURITY.md` — how to report security issues privately, rotation guidance for leaked keys
- Optional: 5–10 minute screencast walkthrough linked from README

---

## Phase 24: Public Launch Polish

**Goal:** Repo is ready to share publicly with MBA cohorts, on LinkedIn, and via any other channels.

**Status:** 🔲 NOT STARTED

**Depends on:** Phases 20–23 complete.

---

### Sprint 24.1 — Repo Polish

**Deliverables:**
- README rewrite with:
  - Hero image or GIF showing the dashboard
  - One-paragraph value proposition
  - "Deploy on Railway" button (from Phase 21) prominently placed
  - Feature list with screenshots of key pages (Signals, Opportunities, Actions, Outreach)
  - Install paths: Railway primary / Docker secondary
  - Link to `QUICKSTART.md` for the full walkthrough
- `.github/ISSUE_TEMPLATE/`: bug report, feature request, question
- `.github/workflows/ci.yml`: run backend tests on PRs (helps fork maintainers verify their changes)

---

### Sprint 24.2 — Launch Features + Announcement

**Deliverables:**
- `DEMO_MODE=true` env flag loads a curated sample data set (20 signals, 5 opportunities, 8 actions, 3 outreach drafts) so first-time users see the product working immediately
- Optional opt-in anonymous install counter: if `TELEMETRY_OPT_IN=true`, backend pings a public endpoint on first boot with `{version, deploy_platform}` — purely for Swapneet's curiosity. Disabled by default; documented in `SECURITY.md`.
- Cohort announcement:
  - LinkedIn post draft
  - HEC MBA cohort Slack/email post draft
  - Any other channels Swapneet chooses

---

## Progress Tracker

### By Phase

| Phase | Status | Sessions Used | Notes |
|-------|--------|--------------|-------|
| 0 | ✅ Complete | 1/1 | Architecture approved 2026-04-12 |
| 0.5 | ✅ Complete | 1/1 | API stack audit complete 2026-04-12. Proxycurl/Crunchbase/Dealroom/NewsAPI.org replaced. |
| 1 | ✅ Complete | 2/3 | Foundation + DB schema complete |
| 2 | ✅ Complete | 2/4 | 51 tests passing |
| 3 | ✅ Complete | 4/4 | Signal intelligence engine |
| 4 | ✅ Complete | 5/5 | AI reasoning layer |
| 5 | ✅ Complete | 2/2 | People intelligence (PDL + Hunter) |
| 6 | ✅ Complete | 5/5 | Frontend core pages |
| 7 | ✅ Complete | 4/4 | Frontend action pages |
| 8 | ✅ Complete | 3/3 | Email automation |
| 9 | ✅ Complete | 4/4 | 253 BE tests + 45 Playwright E2E — all pass |
| 10 | ✅ Complete | 3/3 | 79% BE coverage, fuzz+security tests, ErrorBoundary |
| 11 | ✅ Complete | 2/2 | Docker stack, JSON logging, README — 2026-04-21 |
| 12 | ✅ Complete | 2/2 | Signal ingestion live ✅, ~450 signals classified ✅, Opportunity Predictor + Fit Scorer + Action Generator all run ✅. Full pipeline end-to-end live. |
| 13 | ✅ Complete | 2/2 | Sprint 13.1 ✅: SEC EDGAR 90-day filter, 0-article logger, Celery ×4. Sprint 13.2 ✅: prompt rewrites (classifier + predictor + fit scorer) — all MBA-specific, grounded, cited |
| 14 | 🔲 Not Started | 0/4 | Post-MVP: Sonnet batch + pre-filter, job board layer, FE pipeline bar, extended thinking, launch package |
| 15 | 🔲 Not Started | 0/4 | Resume & Document Intelligence: upload, Profile Extractor Agent, seniority gate |
| 16 | 🔲 Not Started | 0/3 | Action Page Revamp: enriched context, company filter, intended_effect |
| 17 | 🔲 Not Started | 0/3 | Outreach Expansion: LinkedIn message gen + channel routing |
| 17B | 🔲 Not Started | 0/3 | Target Company Intelligence: profile target list, AI "Find Similar" recommendations |
| 18 | 🔲 Not Started | 0/2 | Signal Disambiguation: domain-qualified queries, pre-filter entity check |
| 19 | 🔲 Not Started | 0/3 | Analytics real data + historical backtesting |
| 20 | 🔲 Not Started | 0/2 | Self-Host Foundations: consolidated `initial.sql`, owner-bootstrap script, hardcode/config audit |
| 21 | 🔲 Not Started | 0/2 | Railway Deploy Template: `railway.json`, "Deploy on Railway" button, E2E smoke test |
| 22 | 🔲 Not Started | 0/2 | First-Run Setup Experience: `/system/status`, per-integration health, `/setup` wizard |
| 23 | 🔲 Not Started | 0/2 | Non-Technical Docs: `QUICKSTART.md` with screenshots, `API-KEYS.md`, LICENSE (MIT), etc. |
| 24 | 🔲 Not Started | 0/2 | Public Launch Polish: README, Issues templates, CI, demo mode, cohort announcement |

**Parallel execution opportunity:** Phases 3–5 (backend) can run in parallel with Phase 6 (frontend), saving ~4–5 sessions. Phases 21 and 22 can run in parallel after Phase 20.

---

## Agent Dispatch Reference (Superpowers)

When starting a phase, use this template prompt in Claude Code:

```
I'm working on Apex Phase [N]: [Phase Name].
Read CLAUDE.md and PLAN.md Phase [N] for full context.
Use /writing-plans to break Phase [N] into atomic tasks.
Then use /dispatching-parallel-agents to spawn:
  - Agent A: [BE task description]
  - Agent B: [FE task description]  
  - Agent C: [QA task description]
Use /using-git-worktrees for each agent.
Each agent must use /test-driven-development.
Use /verification-before-completion before each agent merges.
```

---

## Dependency Map

```
Phase 0 (Architecture Approval)
    ↓
Phase 1 (Foundation) ←─────────────────────────────┐
    ↓                                               │
Phase 2 (Core Backend APIs)                        │
    ↓                                               │
Phase 3 (Signal Intelligence) ──┐    Phase 6 (FE Core) ← Phase 1
Phase 4 (AI Reasoning) ─────────┤    Phase 7 (FE Actions) ← Phase 6
Phase 5 (People Intel) ─────────┘         ↓
    ↓                                Phase 8 (Email Auto)
    └──────── Phase 9 (Full Integration) ────────────┘
                    ↓
            Phase 10 (Hardening)
                    ↓
            Phase 11 (Deployment)
                    ↓
            Phase 12 (Live Production Run)
                    ↓
            Phase 13 (Signal & Agent Quality)
                    ↓
            Phase 14 (Post-MVP Enhancements)
                    ↓
     ┌──────────────┼──────────────────┐
     ↓              ↓                  ↓
Phase 15        Phase 16          Phase 17
(Resume &      (Action Page      (Outreach
 Document       Revamp)           Expansion /
 Intelligence)                    LinkedIn)
     │              │                  │
     └──────┬────────┘                 │
            ↓                          │
     Phase 17B (Target Company ←───────┘
      Intelligence: profile
      target list + AI similar)
            ↓
       Phase 18 (Signal Disambiguation)
            ↓
       Phase 19 (Analytics + Backtesting)
       [requires Phase 14.2 Adzuna]
            ↓
       Phase 20 (Self-Host Foundations)
            ↓
     ┌──────┴──────┐
     ↓             ↓
Phase 21      Phase 22
(Railway     (First-Run
 Template)    Setup UX)
     └──────┬──────┘
            ↓
       Phase 23 (Non-Technical Docs)
       [needs screenshots from 21 + 22]
            ↓
       Phase 24 (Public Launch Polish)
```

> Phases 15, 16, 17 are independent of each other and can run in parallel.
> Phase 17B depends on Phase 15 (profile extraction) and can run after Phase 17.
> Phase 18 requires Phase 14.1 (keyword pre-filter) as its foundation.
> Phase 19 requires Phase 14.2 (Adzuna) for the backtesting sprint.
> Phase 20 is the foundation for all multi-user self-host work.
> Phases 21 and 22 can run in parallel after Phase 20.
> Phase 23 depends on both 21 and 22 (documentation screenshots).
> Phase 24 depends on everything above.

---

## 🔄 How to Start a Dev Session

### Prerequisites (first-time Windows setup)
Redis is NOT installed by default on Windows. Install once:
```powershell
winget install Redis.Redis   # installs to C:\Program Files\Redis\
```

### Start Redis + FastAPI + Celery
```powershell
# Terminal 1 — Redis (must start manually each session)
& "C:\Program Files\Redis\redis-server.exe" --port 6379
# Verify: & "C:\Program Files\Redis\redis-cli.exe" ping  → should return PONG

# Terminal 2 — FastAPI
cd "E:\Claude Projects\Apex\backend"
C:\Python314\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 3 — Celery worker (Windows-safe threads pool)
cd "E:\Claude Projects\Apex\backend"
C:\Python314\python.exe -m celery -A app.core.celery_app worker -Q high,default,low --loglevel=info --pool=threads --concurrency=4 --logfile=celery_worker.log

# Terminal 4 — Frontend
cd "E:\Claude Projects\Apex\frontend"
npm run dev
```

**Quick health check after starting:**
- Backend: `curl http://localhost:8000/api/v1/health` → `{"status":"ok"}`
- Frontend: `http://localhost:3000`

### Get a JWT token
```powershell
cd "E:\Claude Projects\Apex\backend"
echo '{"email":"swapneet.lahoti@gmail.com","password":"Apex2026!"}' > login.json
curl.exe -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" --data-binary "@login.json"
# Copy the access_token from the response
```

### ⚠️ Existing DB installs: run migrations once
If your Supabase DB was created before 2026-04-27, run this once to apply missed migrations:
```powershell
cd "E:\Claude Projects\Apex\backend"
C:\Python314\python.exe scripts/apply_migrations.py
```
This adds: `user_documents` table, `approach_angle` rename, Phase 15 `career_profiles` columns,
`intended_effect` on `actions`, `channel` on `outreach_emails`, `real_postings` on `opportunities`.

### Creating a fresh test user (recommended for QA)
The main account (`swapneet.lahoti@gmail.com`) has 1,446 signals + existing data — not ideal for
observing a clean first-run flow. Create a test user:
1. Go to Supabase dashboard → Authentication → Users → Add user
2. Set email + password, confirm email
3. The user gets a blank profile — perfect for testing the full happy path

### Current DB State (as of 2026-04-27)
| Metric | Value |
|--------|-------|
| Total signals in DB | 1,446 |
| Signals classified | ~450 |
| Signals with embeddings | ~280 (those that passed relevance gate) |
| Opportunities | Predicted (Opportunity Predictor ran) |
| Actions | Generated (Action Generator ran) |
| DB migrations applied | 001–019 (all current as of 2026-04-27) |
| `.gitignore` | Added login.json, ingest.json, celerybeat-schedule* exclusions |

---

*Update this file after every session. Mark tasks ✅ when complete. Never skip Phase 0 approval.*
