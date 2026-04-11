# PLAN.md — Apex Platform: Full Development Plan

> **Living document.** Update after every session. Mark tasks ✅ when complete.
> Last updated: 2026-04-12 | Current Phase: **Phase 0 — Architecture Review & Approval**

---

## Project Timeline Overview

| Phase | Name | Focus | BE Agents | FE Agents | QA Agents | Est. Sessions |
|-------|------|-------|-----------|-----------|-----------|--------------|
| 0 | Architecture Review & Approval | Design lock-in, no code | 0 | 0 | 0 | 1 |
| 1 | Project Foundation | Repo, DB schema, scaffolds | 1 | 1 | 1 | 2–3 |
| 2 | Core Backend APIs | Users, Companies, Signals CRUD | 2 | 0 | 1 | 3–4 |
| 3 | Signal Intelligence Engine | Ingestion workers, classifiers | 2 | 0 | 1 | 3–4 |
| 4 | AI Reasoning Layer | Opportunity prediction, fit scoring | 2 | 0 | 1 | 4–5 |
| 5 | People Intelligence | Proxycurl enrichment, contacts | 1 | 0 | 1 | 2 |
| 6 | Frontend — Core Pages | Dashboard, Signals, Opportunities | 0 | 2 | 1 | 4–5 |
| 7 | Frontend — Action Pages | Actions, Outreach, Profile | 0 | 2 | 1 | 3–4 |
| 8 | Email Automation | Gmail OAuth, drafts, sends | 1 | 1 | 1 | 2–3 |
| 9 | Full Integration & E2E | Wire FE↔BE, real data | 1 | 1 | 2 | 3–4 |
| 10 | Testing & Hardening | Coverage, perf, security | 0 | 0 | 3 | 2–3 |
| 11 | v1.0 Deployment | Docker, prod config | 1 | 0 | 1 | 1–2 |

**Total estimated sessions (with ~2hr model limit each): 30–40 sessions**

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

**Status:** 🔄 IN PROGRESS

### 0.1 Architecture Approval Checklist

- [ ] **Data model review** — Review all tables in CLAUDE.md Section 4. Confirm field names, types, relationships.
- [ ] **API design review** — Review all endpoints in CLAUDE.md Section 7. Confirm naming, methods, response shapes.
- [ ] **Agent orchestration review** — Review agent types in CLAUDE.md Section 5. Confirm model choices (Sonnet vs Haiku).
- [ ] **Signal sources review** — Review sources in CLAUDE.md Section 14. Confirm which APIs you have access to.
- [ ] **Frontend page scope review** — Review pages in CLAUDE.md Section 6. Confirm all 8 pages are in scope for v1.0.
- [ ] **Tech stack final confirmation** — Review CLAUDE.md Section 2. Any changes before we start?
- [ ] **Environment variables** — Do you have API keys for: Anthropic, OpenAI, Proxycurl, NewsAPI, Crunchbase, Gmail?
- [ ] **Supabase project** — Is a Supabase project created? Do you have the connection strings?

### 0.2 Decisions to Make Before Phase 1

1. **Auth scope for v1.0** — Single hardcoded user (simplest) OR Supabase Auth with login page?
   - Recommendation: Supabase Auth from day one (cohort-ready requirement)
   
2. **Signal ingestion trigger for v1.0** — Manual (button click) OR automatic (Celery cron)?
   - Recommendation: Both — cron runs every 4 hours, manual button for testing
   
3. **Email automation for v1.0** — Draft only (user sends manually) OR auto-send?
   - Recommendation: Draft + confirm step (user approves before send)

4. **Analytics scope for v1.0** — Full analytics page OR basic dashboard stats?
   - Recommendation: Dashboard stats only for v1.0, full analytics in v1.5

### 0.3 Architecture Approval Sign-Off

> **APPROVAL REQUIRED BEFORE PHASE 1 STARTS**
> 
> When you've reviewed and approved the architecture, add your confirmation here:
> 
> **Approved by:** _________________________ **Date:** _____________
> **Notes/Changes:**

---

## Phase 1: Project Foundation

**Goal:** Working repo with scaffolded BE + FE, Supabase schema deployed, Docker dev environment running.

**Status:** ⏳ PENDING (awaiting Phase 0 approval)

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (BE + FE + QA)

### Sprint 1.1 — Repository & Infrastructure (Session 1)

**Agent: BE Infrastructure Agent (1 agent)**

#### Tasks
- [ ] Initialize Python project with `pyproject.toml` (Poetry)
- [ ] Install: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `asyncpg`, `supabase`, `pydantic[email]`, `anthropic`, `openai`, `celery[redis]`, `httpx`, `python-jose`, `passlib`
- [ ] Create `backend/app/core/config.py` — Settings class using Pydantic BaseSettings, reads from `.env`
- [ ] Create `docker-compose.yml` with: FastAPI, Redis, Celery worker
- [ ] Create `.env.example` with all required vars (see CLAUDE.md Section 8)
- [ ] Create `backend/Dockerfile`
- [ ] Verify: `docker-compose up` starts without errors

**Agent: FE Infrastructure Agent (1 agent)**

#### Tasks
- [ ] Initialize Next.js 14 project: `npx create-next-app@latest frontend --typescript --tailwind --app`
- [ ] Install: `shadcn/ui`, `lucide-react`, `@supabase/supabase-js`, `@tanstack/react-query`, `axios`, `recharts`
- [ ] Initialize shadcn/ui: `npx shadcn-ui@latest init`
- [ ] Install shadcn components: `card`, `badge`, `progress`, `button`, `input`, `dialog`, `sheet`, `tabs`, `select`, `separator`
- [ ] Migrate `Index.tsx` → `frontend/app/(dashboard)/page.tsx` (adapt to Next.js app router)
- [ ] Create `frontend/components/layout/DashboardLayout.tsx` (sidebar nav to all 8 pages)
- [ ] Create `frontend/lib/mock/index.ts` — all mock data from Loveable design
- [ ] Verify: `npm run dev` shows dashboard with mock data

**Agent: QA Infrastructure Agent (1 agent)**

#### Tasks
- [ ] Set up pytest with `pytest-asyncio`, `httpx`, `pytest-cov`
- [ ] Set up Vitest + React Testing Library in frontend
- [ ] Set up Playwright for E2E (`npx playwright install`)
- [ ] Create `backend/tests/conftest.py` — test client, test DB fixtures
- [ ] Write smoke test: GET `/api/v1/health` returns 200
- [ ] Write FE smoke test: Dashboard renders without crashing

### Sprint 1.2 — Database Schema (Session 2)

**Agent: BE Database Agent (1 agent)**

#### Tasks
- [ ] Create Supabase migrations for all tables (CLAUDE.md Section 4):
  - [ ] `users` table
  - [ ] `career_profiles` table (with embedding vector[1536])
  - [ ] `companies` table
  - [ ] `contacts` table
  - [ ] `signals` table (with embedding vector[1536])
  - [ ] `opportunities` table
  - [ ] `actions` table
  - [ ] `outreach_emails` table
- [ ] Enable Row Level Security on ALL tables
- [ ] Create RLS policies: all SELECT/INSERT/UPDATE/DELETE filtered by `user_id = auth.uid()`
- [ ] Create indexes: `signals(user_id, company_id, signal_date)`, `opportunities(user_id, confidence)`, `actions(user_id, status, priority)`
- [ ] Create pgvector index on `career_profiles.embedding` and `signals.embedding`
- [ ] Run migrations against Supabase dev project
- [ ] Seed dev data: 1 test user, 5 companies, 10 signals, 3 opportunities, 5 actions

#### Verification
```bash
# Run from backend/
pytest tests/integration/test_db.py -v
# All tables exist, RLS policies work, seed data loads
```

---

## Phase 2: Core Backend APIs

**Goal:** All CRUD endpoints for signals, opportunities, actions, profile, companies working with real Supabase data. Auth middleware working.

**Status:** ⏳ PENDING

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 BE + 1 QA) → `/test-driven-development`

**Pre-requisite:** Phase 1 complete ✅

### Sprint 2.1 — Auth & Base Setup (Session 3)

**Agent: BE Auth Agent (1 agent)**

#### Tasks
- [ ] Create `backend/app/core/security.py` — JWT validation via Supabase
- [ ] Create `backend/app/core/dependencies.py` — `get_current_user` dependency
- [ ] Create `backend/app/api/v1/__init__.py` — Router aggregation
- [ ] Create `backend/app/api/v1/health.py` — `GET /api/v1/health`
- [ ] Create `backend/app/api/v1/auth.py` — Auth endpoints (login, refresh)
- [ ] All endpoints return structured JSON errors (never raw exceptions)

### Sprint 2.2 — Core Resource APIs (Sessions 4–5)

**Agent: BE API Agent A — Signals + Companies (1 agent)**

#### Tasks (TDD: write test first, then implement)
- [ ] `backend/app/models/signal.py` — SQLAlchemy + Pydantic models
- [ ] `backend/app/models/company.py`
- [ ] `backend/app/services/signal_service.py` — CRUD logic
- [ ] `backend/app/services/company_service.py`
- [ ] `backend/app/api/v1/signals.py` — All signal endpoints
  - [ ] `GET /signals` — paginated, filter by type/company/date_from/date_to
  - [ ] `GET /signals/{id}` — with linked opportunities
  - [ ] `POST /signals/ingest` — trigger manual ingest (enqueues Celery task)
- [ ] `backend/app/api/v1/companies.py`
  - [ ] `GET /companies/{id}` — with signal summary

**Agent: BE API Agent B — Opportunities + Actions + Profile (1 agent)**

#### Tasks (TDD: write test first, then implement)
- [ ] `backend/app/models/opportunity.py`
- [ ] `backend/app/models/action.py`
- [ ] `backend/app/models/profile.py`
- [ ] `backend/app/services/opportunity_service.py`
- [ ] `backend/app/services/action_service.py`
- [ ] `backend/app/services/profile_service.py`
- [ ] `backend/app/api/v1/opportunities.py`
  - [ ] `GET /opportunities` — filter by confidence/status/company
  - [ ] `GET /opportunities/{id}` — full detail with signals
  - [ ] `POST /opportunities/{id}/refresh` — re-score (enqueues task)
- [ ] `backend/app/api/v1/actions.py`
  - [ ] `GET /actions` — filter by status/priority
  - [ ] `PUT /actions/{id}` — update status
  - [ ] `POST /actions/{id}/draft-email` — enqueue email draft generation
- [ ] `backend/app/api/v1/profile.py`
  - [ ] `GET /profile` — career profile
  - [ ] `PUT /profile` — update profile

**Agent: QA API Agent (1 agent)**

#### Tasks
- [ ] Integration tests for ALL endpoints (real test DB, no mocks)
- [ ] Test auth: unauthenticated requests get 401
- [ ] Test RLS: user A cannot see user B's data
- [ ] Test pagination: large datasets return correct pages
- [ ] Test filters: all filter params work correctly
- [ ] Coverage report: ≥ 80% on all service files

#### Phase 2 Verification
```bash
pytest tests/integration/ -v --cov=app --cov-report=term-missing
# All tests pass. Coverage ≥ 80%.
```

---

## Phase 3: Signal Intelligence Engine

**Goal:** Automatic signal ingestion from all 5 sources, running on Celery workers, signals classified and stored in Supabase.

**Status:** ⏳ PENDING

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (2 BE + 1 QA)

**Pre-requisite:** Phase 2 complete ✅

### Sprint 3.1 — Signal Ingestion Workers (Sessions 6–7)

**Agent: BE Signal Ingestion Agent A (1 agent)**

#### Tasks
- [ ] `backend/app/integrations/newsapi_client.py`
  - Fetch articles by company name + keyword
  - Parse and normalize to signal format
- [ ] `backend/app/integrations/crunchbase_client.py`
  - Fetch funding rounds, acquisitions, leadership hires
  - Parse and normalize to signal format
- [ ] `backend/app/integrations/rss_client.py`
  - Configurable RSS feed list
  - Parse and normalize to signal format
- [ ] `backend/app/workers/ingest_signals.py` (Celery tasks)
  - `ingest_from_newsapi(user_id, company_ids)`
  - `ingest_from_crunchbase(user_id, company_ids)`
  - `ingest_from_rss(user_id, feed_urls)`
  - Deduplication: hash(source + url + date) before insert

**Agent: BE Signal Ingestion Agent B (1 agent)**

#### Tasks
- [ ] `backend/app/integrations/sec_edgar_client.py`
  - Fetch 8-K filings for tracked companies
  - Parse for: exec changes, major contracts, material events
- [ ] `backend/app/integrations/dealroom_client.py`
  - Fetch funding rounds and investor data (EU focus)
- [ ] `backend/app/workers/classify_signals.py` (Celery tasks)
  - `classify_signal(signal_id)` — calls Haiku to classify type + relevance
  - `batch_classify_signals(signal_ids[])` — bulk classification
  - `embed_signal(signal_id)` — generate + store embedding
- [ ] `backend/app/core/celery_app.py` — Celery configuration
  - Beat schedule: ingest every 4 hours
  - Priority queues: `high`, `default`, `low`

### Sprint 3.2 — Signal Classifier Agent (Session 8)

**Agent: BE AI Classification Agent (1 agent)**

#### Tasks
- [ ] `backend/app/agents/signal_classifier.py`
  - System prompt: classify signal type from SIGNAL_TYPES enum
  - Score relevance (0–1) for user's target industries/roles
  - Extract: companies mentioned, people mentioned, key facts
  - Use Claude Haiku (cost-efficient, high volume)
  - Include prompt caching for system prompt
- [ ] `backend/app/agents/base_agent.py` — base class with retry logic, logging
- [ ] Snapshot tests for classifier: test fixtures of 10 real signal types
- [ ] Validate: classification accuracy ≥ 85% on test fixtures

**Agent: QA Signal Agent (1 agent)**

#### Tasks
- [ ] Unit tests for each integration client (record/replay fixtures)
- [ ] Integration test: ingest → classify → store pipeline end-to-end
- [ ] Test deduplication: same signal ingested twice → stored once
- [ ] Test Celery task retry on API failures
- [ ] Load test: 100 signals classified in < 60 seconds

#### Phase 3 Verification
```bash
# Trigger manual ingest
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

**Goal:** Enrich companies and contacts via Proxycurl. User can search for key contacts at target companies.

**Status:** ⏳ PENDING

**Superpowers Skills:** `/writing-plans` → `/dispatching-parallel-agents` (1 BE + 1 QA)

**Pre-requisite:** Phase 4 complete ✅

### Sprint 5.1 — Proxycurl Integration (Session 11)

**Agent: BE Enrichment Agent (1 agent)**

#### Tasks
- [ ] `backend/app/integrations/proxycurl_client.py`
  - `get_company(linkedin_url)` → company profile + headcount + recent hires
  - `get_person(linkedin_url)` → contact profile
  - `search_people(company_name, title_keywords)` → list of contacts
  - Rate limiting: respect Proxycurl's rate limits, queue with Celery
  - Cache enriched data: re-enrich only if > 30 days old
- [ ] `backend/app/workers/enrich_contacts.py`
  - `enrich_company(company_id)` — fetch Proxycurl company data
  - `enrich_contact(contact_id)` — fetch Proxycurl person data
  - `find_key_contact(company_id, role_type)` — search + auto-create contact
- [ ] `backend/app/api/v1/contacts.py`
  - `GET /contacts` — user's saved contacts
  - `POST /contacts/search` — search Proxycurl by company + title
  - `GET /contacts/{id}` — contact detail

**Agent: QA Enrichment Agent (1 agent)**

#### Tasks
- [ ] Mock Proxycurl responses (avoid API costs in tests)
- [ ] Test enrichment: company enriched with correct fields
- [ ] Test contact search: returns ranked contacts by seniority
- [ ] Test caching: second enrichment uses cache, not API

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
| 0 | 🔄 In Progress | 0/1 | Need architecture approval |
| 1 | ⏳ Pending | 0/3 | |
| 2 | ⏳ Pending | 0/4 | |
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
