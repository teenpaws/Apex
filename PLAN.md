# PLAN.md — Apex Platform: Full Development Plan

> **Living document.** Update after every session. Mark tasks ✅ when complete.
> Last updated: 2026-04-12 | Current Phase: **Phase 3 — Signal Intelligence Engine**

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

**Total estimated sessions (with ~2hr model limit each): 30–40 sessions**

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

**Status:** ⏳ PENDING

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 BE + 1 QA)

**Pre-requisite:** Phase 3 complete ✅

### Sprint 4.1 — Opportunity Predictor (Sessions 9–10)

**Agent: BE Opportunity Agent (1 agent)**

#### Tasks
- [ ] `backend/app/agents/opportunity_predictor.py`
  - Input: company signals + user career profile
  - Output: predicted role, confidence (HIGH/MEDIUM/SPECULATIVE), timeline_weeks, why_it_fits, positioning_notes
  - Use Claude Sonnet with prompt caching on system prompt
  - Chain-of-thought reasoning: signals → company needs → role prediction
  - Prompt template must reference user's target roles and industries
- [ ] `backend/app/agents/career_fit_scorer.py`
  - Input: predicted opportunity + user career profile embedding
  - Output: fit_score (0–100), fit_explanation, skill_gaps, strengths
  - Compare user embedding vs opportunity requirements (cosine similarity)
  - Claude Sonnet for nuanced fit reasoning
- [ ] `backend/app/workers/predict_opportunities.py` (Celery)
  - `predict_for_company(user_id, company_id)` — runs after new signals
  - `score_opportunity_fit(user_id, opportunity_id)`
  - Triggered automatically after signal classification

**Agent: BE Action Generator Agent (1 agent)**

#### Tasks
- [ ] `backend/app/agents/positioning_advisor.py`
  - Input: user profile + opportunity + company signals
  - Output: positioning narrative (2–3 paragraphs), key talking points, recommended approach angle
  - Claude Sonnet
- [ ] `backend/app/agents/contact_identifier.py`
  - Input: company name + predicted role type
  - Output: ideal contact title to approach, search query for Proxycurl
  - Claude Haiku (fast lookup)
- [ ] `backend/app/agents/action_generator.py`
  - Input: opportunity + fit score + contacts
  - Output: list of ActionItem objects (title, description, type, priority, due_date)
  - Priority scoring: urgency × confidence × fit_score
  - Claude Haiku (structured output generation)
- [ ] `backend/app/workers/generate_actions.py` (Celery)
  - `generate_actions_for_opportunity(user_id, opportunity_id)`
  - Runs after opportunity is created + scored

**Agent: QA Reasoning Agent (1 agent)**

#### Tasks
- [ ] Snapshot tests for all 5 agent prompts
  - Test with 10 recorded signal fixtures → expected output shape
- [ ] Test opportunity prediction: given funding signal → predicts "VP of [function]"
- [ ] Test fit scoring: MBA profile + strategy role → score ≥ 70
- [ ] Test action generation: 1 opportunity → 2–4 actions with correct priority
- [ ] Verify Claude API costs: average cost per opportunity prediction < $0.10

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

**Status:** ⏳ PENDING

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (1 BE + 1 QA)

**Pre-requisite:** Phase 4 complete ✅

### Sprint 5.1 — PDL + Hunter.io Integration (Session 11)

**Agent: BE Enrichment Agent (1 agent)**

#### Tasks
- [ ] `backend/app/integrations/pdl_client.py`
  - People Data Labs REST API — replaces Proxycurl
  - `enrich_person(name, company, linkedin_url=None)` → contact profile
  - `enrich_company(name, domain=None)` → company profile + headcount
  - `search_people(company_name, title_keywords)` → list of matching contacts
  - Free tier: 1,000 credits/month — cache ALL enriched profiles (90-day TTL)
  - Data is sourced from public/open data (no LinkedIn scraping) — legally clean
  - Error handling: on 402 (quota exceeded) → log warning, return cached data or None
- [ ] `backend/app/integrations/hunter_client.py`
  - Hunter.io REST API — email finding by company domain + person name
  - `find_email(first_name, last_name, domain)` → verified email or None
  - `find_domain_emails(domain, limit=5)` → list of known emails at a company
  - Free tier: 25 searches/month — use sparingly, only for high-priority contacts
  - Cache results permanently (emails don't change often)
- [ ] `backend/app/workers/enrich_contacts.py` (REBUILT)
  - `enrich_company(company_id)` → calls pdl_client.enrich_company()
  - `enrich_contact(contact_id)` → calls pdl_client.enrich_person(), then hunter_client.find_email()
  - `find_key_contact(company_id, role_type)` → PDL search + auto-create contact record
  - Quota-aware: track monthly PDL credit usage in agent_runs table
  - Prioritize enrichment queue by opportunity fit_score (enrich high-fit contacts first)
- [ ] `backend/app/api/v1/contacts.py` (unchanged interface — same endpoints)
  - `GET /contacts` — user's saved contacts
  - `POST /contacts/search` — search PDL by company + title (was Proxycurl)
  - `GET /contacts/{id}` — contact detail

**Agent: QA Enrichment Agent (1 agent)**

#### Tasks
- [ ] Mock PDL API responses (record/replay fixtures — avoid using credits in tests)
- [ ] Mock Hunter.io responses (same pattern)
- [ ] Test enrichment: company enriched with correct fields from PDL
- [ ] Test contact search: returns ranked contacts by seniority
- [ ] Test caching: second enrichment uses cache, not API (critical for quota)
- [ ] Test quota tracking: agent_runs records PDL credit consumption
- [ ] Test graceful degradation: when PDL quota exhausted, system returns cached data not error

---

## Phase 6: Frontend — Core Pages

**Goal:** Dashboard, Signals page, and Opportunities page fully functional with real API data. Mock data removed from these pages.

**Status:** ⏳ PENDING

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 FE + 1 QA)

**Pre-requisite:** Phase 2 complete ✅ (can run in parallel with Phases 3–5)

### Sprint 6.1 — API Client & State Layer (Session 12)

**Agent: FE Foundation Agent (1 agent)**

#### Tasks
- [ ] `frontend/lib/api/client.ts` — axios instance with auth headers
- [ ] `frontend/lib/api/signals.ts` — signal API functions
- [ ] `frontend/lib/api/opportunities.ts` — opportunity API functions
- [ ] `frontend/lib/api/actions.ts` — action API functions
- [ ] `frontend/lib/api/profile.ts` — profile API functions
- [ ] `frontend/hooks/useSignals.ts` — React Query hook
- [ ] `frontend/hooks/useOpportunities.ts` — React Query hook
- [ ] `frontend/hooks/useActions.ts` — React Query hook
- [ ] `frontend/types/index.ts` — full TypeScript interfaces for all data models
- [ ] Loading states: skeleton loaders for all data-heavy components
- [ ] Error states: error boundary + retry UI

### Sprint 6.2 — Dashboard & Signals Pages (Sessions 13–14)

**Agent: FE Page Agent A — Dashboard + Signals (1 agent)**

#### Tasks
- [ ] `frontend/app/(dashboard)/page.tsx` — Dashboard (wire to real API)
  - `PipelineViz` component — shows signal→opportunity→action counts
  - Top Predicted Opportunities (High confidence, sorted by timeline)
  - Recent Signals (latest 3, with company + type + date)
  - Priority Actions (todo/in-progress, sorted by due_date)
  - Auto-refresh every 5 minutes
- [ ] `frontend/app/(dashboard)/signals/page.tsx` — Full signals page
  - Signal list with virtual scroll (potentially 100s of signals)
  - Filters: type (multi-select), date range, company search, confidence
  - Signal detail side panel (click → expand)
  - Linked opportunities count per signal
  - "Ingest Now" button (calls POST /signals/ingest)
- [ ] `frontend/components/signals/SignalCard.tsx`
- [ ] `frontend/components/signals/SignalFilters.tsx`
- [ ] `frontend/components/signals/SignalDetailPanel.tsx`

**Agent: FE Page Agent B — Opportunities (1 agent)**

#### Tasks
- [ ] `frontend/app/(dashboard)/opportunities/page.tsx`
  - Opportunity cards in grid (3 columns)
  - Filters: confidence, timeline, company, status
  - Sort: by fit score, by timeline, by confidence
  - Opportunity detail modal:
    - Role + company header
    - Why this fits (AI-generated)
    - Positioning notes (AI-generated)
    - Key contact (with LinkedIn link)
    - Predicted salary range
    - Source signals (linked)
    - Actions triggered by this opportunity
    - "Create Action" button
    - "Refresh Analysis" button
  - Confidence badges use design system colors (CLAUDE.md Section 6)
- [ ] `frontend/components/opportunities/OpportunityCard.tsx`
- [ ] `frontend/components/opportunities/OpportunityDetail.tsx`
- [ ] `frontend/components/opportunities/OpportunityFilters.tsx`

**Agent: QA FE Agent (1 agent)**

#### Tasks
- [ ] Vitest tests for all new components (render, interaction)
- [ ] Test filter state: selecting confidence=High filters list
- [ ] Test API integration: mock API responses, verify data renders
- [ ] Playwright E2E: Dashboard loads with real data, signals page filter works, opportunity modal opens
- [ ] Responsive design check: mobile (375px), tablet (768px), desktop (1440px)

---

## Phase 7: Frontend — Action Pages

**Goal:** Actions page, Outreach page, Profile page, and Settings page fully functional.

**Status:** ⏳ PENDING

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 FE + 1 QA)

**Pre-requisite:** Phase 6 complete ✅

### Sprint 7.1 — Actions & Outreach Pages (Sessions 15–16)

**Agent: FE Page Agent A — Actions (1 agent)**

#### Tasks
- [ ] `frontend/app/(dashboard)/actions/page.tsx`
  - Kanban board view: Todo | In Progress | Done columns (drag-and-drop)
  - List view alternative (toggle)
  - Filter: priority, type, company, due date
  - Action card: title, company, priority badge, due date, source signal
  - Click → Action detail: full description, opportunity link, "Draft Email" button
  - Status update: drag or dropdown
  - Mark done / snooze actions
- [ ] `frontend/components/actions/ActionKanban.tsx`
- [ ] `frontend/components/actions/ActionCard.tsx`
- [ ] `frontend/components/actions/ActionDetail.tsx`

**Agent: FE Page Agent B — Outreach + Profile (1 agent)**

#### Tasks
- [ ] `frontend/app/(dashboard)/outreach/page.tsx`
  - Email draft list: pending / sent / replied
  - Draft card: recipient name + title, subject line preview, AI confidence
  - Email composer modal:
    - To field (contact search)
    - Subject line (AI-generated, editable)
    - Body (AI-generated, full editor)
    - Tone selector: Professional / Warm / Direct
    - "Regenerate" button (re-calls AI)
    - "Send via Gmail" button
  - Sent tracking: opened indicator, replied indicator
- [ ] `frontend/app/(dashboard)/profile/page.tsx`
  - Career profile form: current role, target roles (multi-select), industries, aspirations text
  - Profile completeness progress bar
  - "Analyze Profile" button → calls AI re-analysis
  - Career trajectory visualization (target roles timeline)
  - Skills input (tags)
- [ ] `frontend/app/(dashboard)/settings/page.tsx`
  - API key status indicators (green/red)
  - Signal source toggles (enable/disable each source)
  - Notification preferences
  - Connected accounts (Gmail OAuth connect/disconnect button)
  - Ingest frequency setting (hourly / 4h / daily)

### Sprint 7.2 — Analytics Page (Session 17)

**Agent: FE Analytics Agent (1 agent)**

#### Tasks
- [ ] `frontend/app/(dashboard)/analytics/page.tsx`
  - Dashboard stats: total signals this week, new opportunities, actions completed
  - Signal velocity chart (recharts): signals per day, by type (stacked area)
  - Pipeline funnel (recharts): signals → opportunities → actions → outreach → replies
  - Company distribution: top 10 companies by signal count (bar chart)
  - Response rate tracker: outreach sent vs replied (over time)

---

## Phase 8: Email Automation

**Goal:** Users can generate AI-drafted emails and send them via Gmail with one click. Sent emails tracked.

**Status:** ⏳ PENDING

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (1 BE + 1 FE + 1 QA)

**Pre-requisite:** Phases 5 + 7 complete ✅

### Sprint 8.1 — Gmail Integration (Sessions 18–19)

**Agent: BE Email Agent (1 agent)**

#### Tasks
- [ ] `backend/app/integrations/gmail_client.py`
  - OAuth 2.0 flow: redirect URI, token exchange, refresh tokens
  - Store tokens encrypted in Supabase (per user)
  - `send_email(user_id, to_email, subject, body)` → returns gmail_message_id
  - `check_replies(user_id, message_ids[])` → returns reply status
- [ ] `backend/app/agents/email_drafter.py`
  - Input: action + contact + opportunity + user_profile
  - Output: subject, body, tone, key_points_used
  - Claude Sonnet with prompt caching
  - 3 tone variants: Professional, Warm, Direct
  - Personalization: references specific signal that triggered the opportunity
- [ ] `backend/app/api/v1/outreach.py`
  - `GET /outreach` — list drafts + sent
  - `POST /outreach/draft` — generate email draft
  - `POST /outreach/{id}/send` — send via Gmail
  - `POST /outreach/oauth/connect` — start Gmail OAuth
  - `GET /outreach/oauth/callback` — complete OAuth

**Agent: FE Email Agent (1 agent)**

#### Tasks
- [ ] Wire outreach page to real API (remove mock data)
- [ ] Gmail OAuth connect flow (Settings page → connect button)
- [ ] Real-time draft generation (loading state while AI generates)
- [ ] Send confirmation dialog
- [ ] Success/failure toast notifications

**Agent: QA Email Agent (1 agent)**

#### Tasks
- [ ] Test email draft generation with real Claude API
- [ ] Mock Gmail API for send tests
- [ ] Test OAuth token refresh flow
- [ ] Test: drafts saved if user closes modal before sending
- [ ] E2E test: draft generated → reviewed → sent (with mock Gmail)

---

## Phase 9: Full Integration & E2E

**Goal:** All systems talking to each other. Real data flows from signal ingestion → opportunities → actions → outreach. Remove ALL mock data from frontend.

**Status:** ⏳ PENDING

**Superpowers Skills:** `/verification-before-completion`

**Pre-requisite:** Phases 6, 7, 8 complete ✅

### Sprint 9.1 — Integration (Sessions 20–22)

**Agent: Integration Agent (1 BE + 1 FE, working together)**

#### Tasks
- [ ] Remove ALL mock data from `frontend/lib/mock/`
- [ ] Wire `GET /api/v1/analytics/dashboard` — return real stats
- [ ] Implement `GET /api/v1/analytics/dashboard` in backend
- [ ] Verify: PipelineViz shows real counts
- [ ] Test full pipeline: signal ingested → classified → opportunity predicted → action created → email drafted
- [ ] Test with real company: pick one company, run full pipeline end-to-end
- [ ] Fix all integration bugs

**Agent: QA Integration Agent (2 agents)**

#### Tasks
- [ ] Playwright E2E tests for all 8 pages with real data
- [ ] Test full user journey: login → dashboard → signal → opportunity → draft email → send
- [ ] Test with 0 data (empty state UIs for all pages)
- [ ] Performance: dashboard loads < 2 seconds on localhost
- [ ] Check: no console errors on any page

---

## Phase 10: Testing & Hardening

**Goal:** Production-ready code quality. 80%+ coverage. Security audit. Performance baseline.

**Status:** ⏳ PENDING

**Pre-requisite:** Phase 9 complete ✅

### Sprint 10.1 — Coverage & Security (Sessions 23–25)

**Agent: QA Hardening Agent A (1 agent)**
- [ ] Achieve 80% test coverage on all backend services
- [ ] Achieve 70% test coverage on all frontend components
- [ ] Fuzz test all API endpoints with invalid inputs
- [ ] SQL injection: verify all queries are parameterized
- [ ] XSS: verify all user content is escaped in frontend

**Agent: QA Hardening Agent B (1 agent)**
- [ ] Rate limiting on all API endpoints (100 req/min per user)
- [ ] API key exposure scan (no keys in git history)
- [ ] Test Celery worker crash recovery
- [ ] Test Redis connection loss recovery
- [ ] Performance test: 100 signals classified in < 60 seconds

**Agent: QA Hardening Agent C (1 agent)**
- [ ] Playwright visual regression tests (screenshots for all 8 pages)
- [ ] Mobile responsiveness test (all pages on 375px)
- [ ] Accessibility audit (axe-core on all pages)
- [ ] Error boundary tests: API down → graceful error UI

---

## Phase 11: v1.0 Deployment

**Goal:** Apex running on a real server (or local with production config) for the primary user.

**Status:** ⏳ PENDING

**Pre-requisite:** Phase 10 complete ✅

### Sprint 11.1 — Production Config (Sessions 26–27)

**Agent: BE Deployment Agent (1 agent)**

#### Tasks
- [ ] Production `docker-compose.prod.yml`
  - FastAPI with Gunicorn workers
  - Celery worker + beat scheduler
  - Redis
  - Nginx reverse proxy
- [ ] Environment separation: dev / staging / prod configs
- [ ] Database: run migrations on prod Supabase project
- [ ] Logging: structured JSON logs (all agents log decisions)
- [ ] Health checks: all services have `/health` endpoints
- [ ] Create startup checklist in README

#### Phase 11 Verification
```
1. docker-compose -f docker-compose.prod.yml up
2. All services start without errors
3. POST /api/v1/signals/ingest works
4. Full pipeline runs end-to-end on prod Supabase
5. Frontend served via Nginx on port 80
```

---

## Progress Tracker

### By Phase

| Phase | Status | Sessions Used | Notes |
|-------|--------|--------------|-------|
| 0 | ✅ Complete | 1/1 | Architecture approved 2026-04-12 |
| 0.5 | ✅ Complete | 1/1 | API stack audit complete 2026-04-12. Proxycurl/Crunchbase/Dealroom/NewsAPI.org replaced. |
| 1 | ✅ Complete | 2/3 | Foundation + DB schema complete |
| 2 | ✅ Complete | 2/4 | 51 tests passing |
| 3 | ⏳ Pending | 0/4 | |
| 4 | ⏳ Pending | 0/5 | |
| 5 | ⏳ Pending | 0/2 | |
| 6 | ⏳ Pending | 0/5 | Can run parallel with 3–5 |
| 7 | ⏳ Pending | 0/4 | |
| 8 | ⏳ Pending | 0/3 | |
| 9 | ⏳ Pending | 0/4 | |
| 10 | ⏳ Pending | 0/3 | |
| 11 | ⏳ Pending | 0/2 | |

**Parallel execution opportunity:** Phases 3–5 (backend) can run in parallel with Phase 6 (frontend), saving ~4–5 sessions.

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
```

---

*Update this file after every session. Mark tasks ✅ when complete. Never skip Phase 0 approval.*
