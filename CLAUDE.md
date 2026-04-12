# CLAUDE.md — Apex Platform: The Holy Grail Dev Reference

> **This file is the single source of truth for all development on the Apex platform.**
> Read this before starting any session. Update it when decisions change.
> Last updated: 2026-04-12 | Phase 1 Sprint 1.2: COMPLETE ✅ | Next: Phase 2 — Core Backend APIs

---

## 1. What Is Apex?

Apex is a multi-agent AI platform that gives job seekers — starting with MBA graduates — a genuine unfair advantage in the job market. It does three things no single tool currently does:

1. **Real-time market intelligence** — predicts hiring 4–12 weeks before roles are posted by monitoring funding rounds, leadership changes, M&A activity, earnings calls, government contracts, and news.
2. **Deep career intelligence** — understands who you want to become (aspirations), not just who you are (resume).
3. **Automated action engine** — turns insights into personalized outreach with minimal manual effort.

**The core insight:** Job boards show what companies advertise. Apex shows what companies *need*.

### Build Stages
| Stage | Scope | Status |
|-------|-------|--------|
| v1.0 | Single user (HEC Paris MBA) | In development |
| v1.5 | MBA cohort (HEC class) | Architecture ready |
| v2.0 | Mid-management market | Planned |

---

## 2. Tech Stack (FINAL — Do Not Re-Litigate)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend API | Python 3.12 + FastAPI (async) | Pydantic v2, async throughout |
| Database | Supabase (Postgres 15 + pgvector) | vector[1536] for embeddings |
| Task Queue | Celery + Redis | Background signal processing |
| AI Reasoning | Claude Sonnet (`claude-sonnet-4-6`) | Main intelligence layer |
| AI Classifier | Claude Haiku (`claude-haiku-4-5-20251001`) | Signal classification, fast ops |
| Embeddings | OpenAI `text-embedding-3-small` | 1536-dim vectors |
| Frontend | Next.js 14 + Tailwind CSS | App router, shadcn/ui components |
| People/Company Data | Proxycurl API | Contact enrichment |
| Email Automation | Gmail API (OAuth 2.0) | Outreach automation |
| Signal Sources | NewsAPI, Crunchbase API, RSS feeds, SEC EDGAR, Dealroom | Market intelligence |
| Auth | Supabase Auth (JWT) | Row-level security from day one |
| Deployment | Docker + Docker Compose | Dev; production TBD |

---

## 3. Repository Structure

```
apex/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers (v1/)
│   │   ├── core/             # Config, security, dependencies
│   │   ├── models/           # SQLAlchemy/Pydantic models
│   │   ├── services/         # Business logic layer
│   │   ├── agents/           # Claude-powered agent logic
│   │   ├── workers/          # Celery tasks
│   │   ├── integrations/     # External API clients
│   │   └── db/               # Migrations, seeds
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                  # Next.js app router
│   │   ├── (dashboard)/      # Protected routes
│   │   │   ├── page.tsx      # Dashboard (Index.tsx migrated here)
│   │   │   ├── signals/
│   │   │   ├── opportunities/
│   │   │   ├── actions/
│   │   │   ├── outreach/
│   │   │   ├── profile/
│   │   │   └── settings/
│   │   ├── auth/
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/               # shadcn/ui base
│   │   ├── layout/           # DashboardLayout, Sidebar, etc.
│   │   ├── signals/          # Signal-specific components
│   │   ├── opportunities/    # Opportunity components
│   │   ├── actions/          # Action components
│   │   └── shared/           # Reusable across features
│   ├── lib/                  # API client, utils, types
│   ├── hooks/                # Custom React hooks
│   └── types/                # TypeScript interfaces
├── docker-compose.yml
├── .env.example
├── CLAUDE.md                 # This file
└── PLAN.md                   # Phase plan
```

---

## 4. Data Architecture

### Core Data Models

**Users** (`user_id` scoped EVERYWHERE — cohort-ready from day one)
```
users: id, email, full_name, profile_json, preferences_json, created_at
career_profiles: id, user_id, current_role, target_roles[], industries[], 
                 aspirations_text, embedding vector[1536], updated_at
```

**Companies & Contacts**
```
companies: id, name, domain, industry, size_range, location, 
           linkedin_url,                         ← ADDED: required for Proxycurl lookups
           enrichment_json, last_enriched_at
contacts: id, company_id, name, title, linkedin_url, email,
          enrichment_json (Proxycurl), last_enriched_at
```

**Signals** (market intelligence raw data)
```
signals: id, user_id, company_id, type (enum), source, title, 
         description, raw_data_json, signal_date, 
         relevance_score float, processed_at, embedding vector[1536],
         is_duplicate bool DEFAULT false,           ← ADDED: dedup flag for debugging
         dedup_hash text UNIQUE                     ← ADDED: hash(source+url+date)
         
signal_types: FUNDING | EXEC_HIRE | EXPANSION | LAYOFF | 
              JOB_POSTING_PATTERN | MA | CONTRACT | EARNINGS
```

**Opportunities** (predicted roles — AI-generated)
```
opportunities: id, user_id, company_id, predicted_role, 
               confidence (HIGH/MEDIUM/SPECULATIVE),
               timeline_weeks int, why_fit text, 
               positioning_notes text, predicted_salary_range,
               fit_score float,                    ← ADDED: Career Fit Scorer output (0–100)
               key_contact_id, signal_ids[], 
               status (PREDICTED/APPROACHED/INTERVIEWING/CLOSED),
               created_at, updated_at
```

**Actions** (task queue for the user)
```
actions: id, user_id, opportunity_id, company_id, contact_id,
         title, description, type (OUTREACH/FOLLOW_UP/RESEARCH/CALL),
         priority (HIGH/MEDIUM/LOW), status (TODO/IN_PROGRESS/DONE/SNOOZED),
         due_date, source_signal_id, ai_draft_json, created_at
```

**Outreach** (email drafts and sends)
```
outreach_emails: id, user_id, action_id, contact_id,
                 subject, body, tone, draft_json,
                 sent_at, gmail_message_id, opened_at, replied_at,
                 reply_detected_at                 ← ADDED: for tracking response time metrics
```

**Agent Runs** (audit trail for all AI agent invocations — REQUIRED)
```
agent_runs: id, user_id, agent_name, model_used,
            input_hash text,                       ← SHA-256 of prompt input
            output_hash text,                      ← SHA-256 of agent output
            tokens_in int, tokens_out int,
            cost_usd float,                        ← calculated at write time
            duration_ms int,
            status (SUCCESS | FAILED | RETRIED),
            error_message text,                    ← nullable, populated on FAILED
            created_at
            
-- Used for: cost tracking, debugging, prompt versioning, audit, rollback
```

---

## 5. Agent Architecture

### Agent Types
| Agent | Model | Responsibility | File |
|-------|-------|----------------|------|
| Signal Classifier | Claude Haiku | Classify raw signals into types, score relevance (fast, cheap) | `agents/signal_classifier.py` |
| Opportunity Predictor | Claude Sonnet | Analyze signals → predict hiring needs + timeline + ideal contact type | `agents/opportunity_predictor.py` |
| Career Fit Scorer | Claude Sonnet | Score how well user's profile fits a predicted opportunity (0–100) | `agents/career_fit_scorer.py` |
| Positioning Advisor | Claude Sonnet | Generate positioning narrative for user → company | `agents/positioning_advisor.py` |
| Email Drafter | Claude Sonnet | Draft personalized outreach emails (3 tone variants) | `agents/email_drafter.py` |
| Action Generator | Claude Haiku | Convert opportunities → prioritized action items | `agents/action_generator.py` |

> **Note:** `Contact Identifier` was merged into `Opportunity Predictor`. The predictor now outputs
> both the predicted role AND the ideal contact title/search query. This avoids a redundant agent
> hop and reflects the tight coupling between these two outputs.

### Agent Registry
All agents are registered in `backend/app/agents/registry.py` — a single manifest dict:
```python
AGENT_REGISTRY = {
    "signal_classifier":    {"model": "claude-haiku-4-5-20251001",  "version": "1.0", "prompt_file": "prompts/signal_classifier_v1.txt"},
    "opportunity_predictor":{"model": "claude-sonnet-4-6",           "version": "1.0", "prompt_file": "prompts/opportunity_predictor_v1.txt"},
    "career_fit_scorer":    {"model": "claude-sonnet-4-6",           "version": "1.0", "prompt_file": "prompts/career_fit_scorer_v1.txt"},
    "positioning_advisor":  {"model": "claude-sonnet-4-6",           "version": "1.0", "prompt_file": "prompts/positioning_advisor_v1.txt"},
    "email_drafter":        {"model": "claude-sonnet-4-6",           "version": "1.0", "prompt_file": "prompts/email_drafter_v1.txt"},
    "action_generator":     {"model": "claude-haiku-4-5-20251001",  "version": "1.0", "prompt_file": "prompts/action_generator_v1.txt"},
}
```
Use `AGENT_REGISTRY` as the single source of model/version truth — never hardcode model names elsewhere.

### Agent Orchestration Flow (Approved)
```
Signal Ingestion (Celery Worker)
  → [Orchestrator: create agent_run record, assign run_id]
  │
  ├─ Signal Classifier (Haiku)
  │    classify type + score relevance + generate embedding
  │    [GATE: relevance_score < 0.4 → stop, mark signal as low-relevance]
  │
  ├─ Opportunity Predictor (Sonnet)
  │    input: company signals + user career profile
  │    output: predicted_role, confidence, timeline_weeks, 
  │            why_fit, positioning_notes, ideal_contact_title
  │
  ├─ [PARALLEL — both triggered by Opportunity Predictor output]
  │   ├─ Career Fit Scorer (Sonnet)
  │   │    input: opportunity + user profile embedding
  │   │    output: fit_score (0–100), fit_explanation, skill_gaps
  │   │
  │   └─ Positioning Advisor (Sonnet)
  │        input: user profile + opportunity + company signals
  │        output: positioning_narrative, key_talking_points, approach_angle
  │
  ├─ [JOIN: wait for Career Fit Scorer + Positioning Advisor]
  │
  ├─ Action Generator (Haiku)
  │    input: opportunity + fit_score + contacts
  │    output: ActionItem[] with title, type, priority, due_date
  │    priority = urgency × confidence × fit_score
  │
  └─ [Orchestrator: update agent_run status = SUCCESS]

On Demand (user clicks "Draft Email"):
  └─ Email Drafter (Sonnet)
       input: action + contact + opportunity + user_profile
       output: 3 variants (Professional / Warm / Direct)
       each variant: subject, body, key_points_used
```

### Base Agent Class
All agents extend `backend/app/agents/base_agent.py`:
- Automatic retry (3x with exponential backoff on API errors)
- `agent_runs` table write on every invocation (input_hash, output_hash, cost, duration)
- Prompt caching enabled on system prompts (saves ~80% cost on repeated calls)
- Structured output validation via Pydantic before returning

### Mock Mode (Development)
All agents check `settings.MOCK_AGENTS` (env var `MOCK_AGENTS=true`).  
When true: return fixture data from `backend/app/agents/fixtures/` — no Claude API calls.  
This allows full pipeline testing without API keys.  
Mock fixtures live in `backend/app/agents/fixtures/{agent_name}_mock_output.json`.

---

## 6. Frontend Pages & Features

Based on the Loveable-designed frontend (Index.tsx), these pages must be developed:

| Route | Page | Key Features |
|-------|------|-------------|
| `/` | Dashboard | Pipeline viz, Top opportunities (High confidence), Recent signals, Priority actions |
| `/signals` | Signals | Full signal list, filter by type/date/company, signal detail view, linked opportunities |
| `/opportunities` | Opportunities | All predicted opps, confidence filter, timeline, why-fit, key contact, predicted salary |
| `/actions` | Actions | Task queue, priority sorting, status management (Todo/In Progress/Done/Snoozed), due dates |
| `/outreach` | Outreach | Email drafts, Gmail send, template library, send tracking |
| `/profile` | Career Profile | Aspiration capture, skills, target roles/industries, profile completeness |
| `/analytics` | Analytics | Signals over time, conversion pipeline funnel, outreach response rates |
| `/settings` | Settings | API keys, notification prefs, signal source config, connected accounts |

### Frontend Design System (from Index.tsx)
```typescript
// Signal type colors
Funding:              "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
"Exec Hire":          "bg-blue-500/20 text-blue-400 border-blue-500/30"
Expansion:            "bg-violet-500/20 text-violet-400 border-violet-500/30"
"Job Posting Pattern":"bg-amber-500/20 text-amber-400 border-amber-500/30"

// Priority colors
High:     "bg-red-500/20 text-red-400 border-red-500/30"
Medium:   "bg-amber-500/20 text-amber-400 border-amber-500/30"
Low:      "bg-muted text-muted-foreground"

// Confidence colors
High:        "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
Medium:      "bg-amber-500/20 text-amber-400 border-amber-500/30"
Speculative: "bg-muted text-muted-foreground border-border"

// Opportunity cards: violet gradient
"bg-gradient-to-br from-violet-500/10 to-purple-600/5 border-violet-500/20"
```

---

## 7. API Design

### Base URL: `/api/v1/`

#### Core Resources
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check — returns 200 + version |
| GET | `/signals` | List signals (paginated, filterable by type/company/date) |
| GET | `/signals/{id}` | Signal detail + linked opportunities |
| POST | `/signals/ingest` | Trigger manual signal ingest → returns `{run_id}` |
| GET | `/opportunities` | List predicted opportunities (filter: confidence/status/company) |
| GET | `/opportunities/{id}` | Opportunity detail with signals + actions |
| POST | `/opportunities/{id}/refresh` | Re-score with latest signals → returns `{run_id}` |
| GET | `/actions` | List actions (filterable by status/priority/type) |
| PUT | `/actions/{id}` | Update action status/priority/due_date |
| POST | `/actions/{id}/draft-email` | Generate email draft → returns `{run_id}` |
| GET | `/outreach` | List outreach emails (filter: status=draft/sent/replied) |
| POST | `/outreach/draft` | Generate new email draft (contact + action) |
| POST | `/outreach/{id}/send` | Send via Gmail |
| POST | `/outreach/oauth/connect` | Start Gmail OAuth flow → returns redirect URL |
| GET | `/outreach/oauth/callback` | Complete Gmail OAuth (redirect target) |
| GET | `/profile` | Get career profile |
| PUT | `/profile` | Update career profile |
| POST | `/profile/analyze` | Trigger profile re-analysis → returns `{run_id}` |
| GET | `/companies/{id}` | Company detail + signals + opportunities |
| GET | `/contacts` | User's saved contacts |
| POST | `/contacts/search` | Search Proxycurl by company + title keywords |
| GET | `/contacts/{id}` | Contact detail |

#### Agent & Pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents/run-status/{run_id}` | Poll pipeline run status → `{status, progress, result_id}` |
| GET | `/agents/runs` | List recent agent runs (cost dashboard) |

#### Analytics & Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/dashboard` | Dashboard stats (signals/week, new opps, actions done) |
| GET | `/analytics/costs` | Agent cost summary by agent_name + date range |
| POST | `/auth/login` | Supabase auth (email + password) |
| POST | `/auth/refresh` | Refresh JWT token |

### Async Response Pattern
Any endpoint that enqueues a Celery task returns immediately with:
```json
{ "run_id": "uuid", "status": "queued", "message": "Processing started" }
```
Frontend polls `GET /agents/run-status/{run_id}` until `status = SUCCESS | FAILED`.  
Alternatively, Supabase Realtime can be used to subscribe to table updates directly.

### Mock Data Pattern (Development)
All endpoints check `settings.USE_MOCK_DATA` (env var `USE_MOCK_DATA=true`).  
When true: return data from `backend/app/api/mock_responses/` — no DB or AI calls.  
This allows full frontend development without Supabase or API keys configured.

---

## 8. Environment Variables

```bash
# Backend
DATABASE_URL=postgresql://...  # Supabase connection string
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
PROXYCURL_API_KEY=...
NEWS_API_KEY=...
CRUNCHBASE_API_KEY=...
DEALROOM_API_KEY=...
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REDIRECT_URI=...

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

---

## 9. Superpowers Framework Integration

### Installation
```bash
# Clone superpowers into your home directory
git clone https://github.com/obra/superpowers.git ~/.superpowers

# In Claude Code, superpowers skills are available as slash commands
# Key skills used in this project:
/writing-plans          # Before each phase, write a detailed plan
/executing-plans        # Execute the written plan with subagents
/dispatching-parallel-agents  # Run BE + FE + QA agents in parallel
/test-driven-development      # RED-GREEN-REFACTOR for all new code
/systematic-debugging         # When stuck on a bug
/using-git-worktrees          # Isolate each phase in a git worktree
/verification-before-completion  # Always verify before marking done
```

### Parallel Agent Pattern
For each development phase, dispatch agents as follows:
```
Phase N kickoff:
  1. Orchestrator reads PLAN.md Phase N spec
  2. Runs /writing-plans to create phase-specific task breakdown
  3. Dispatches parallel agents via /dispatching-parallel-agents:
     - Agent A: Backend (FastAPI routes, models, services)
     - Agent B: Frontend (Next.js pages, components)
     - Agent C: QA (tests for BE + FE)
  4. Agents work in git worktrees (isolated branches)
  5. /verification-before-completion before merging each agent's work
```

### Git Worktree Convention
```bash
# Create worktrees for parallel development
git worktree add ../apex-be-phase2 -b feature/phase2-backend
git worktree add ../apex-fe-phase2 -b feature/phase2-frontend
git worktree add ../apex-qa-phase2 -b feature/phase2-qa
```

---

## 10. Development Rules (Non-Negotiable)

1. **All DB queries are user_id scoped.** Every table has `user_id`. Every query filters by it. No exceptions.
2. **TDD always.** Write failing tests first. Red → Green → Refactor. No code without a test.
3. **Pydantic for everything.** All API request/response bodies use Pydantic v2 models.
4. **Async FastAPI.** All endpoints and services use `async/await`. No blocking I/O.
5. **Type everything.** Full TypeScript in frontend. No `any` types.
6. **No mock data in production.** Mock data only in `frontend/lib/mock/`. All pages must have a real-data path.
7. **Claude API calls go through the service layer.** Never call Anthropic SDK directly from routes.
8. **Signal processing is async.** All signal ingestion runs in Celery workers, never synchronously.
9. **Environment variables only.** No hardcoded API keys anywhere. Ever.
10. **Superpowers skills before raw coding.** Use `/writing-plans` before any new phase. Use `/test-driven-development` for all new features.

---

## 11. Post-Build Dependencies (Resolve After v1.0 Complete)

> These are known gaps, unresolved dependencies, and deferred work items that are intentionally
> excluded from v1.0 scope. Resolve before v1.5 or production launch.

### API Keys Required (Placeholders In Place)
| Service | Used For | Where Configured | Status |
|---------|---------|-----------------|--------|
| `ANTHROPIC_API_KEY` | All AI agents | `.env` + `settings.py` | ⏳ Pending |
| `OPENAI_API_KEY` | Embeddings (`text-embedding-3-small`) | `.env` + `settings.py` | ⏳ Pending |
| `NEWS_API_KEY` | Signal ingestion — news source | `.env` + `integrations/newsapi_client.py` | ⏳ Pending |
| `CRUNCHBASE_API_KEY` | Signal ingestion — funding rounds | `.env` + `integrations/crunchbase_client.py` | ⏳ Pending |
| `DEALROOM_API_KEY` | Signal ingestion — EU funding | `.env` + `integrations/dealroom_client.py` | ⏳ Pending |
| `PROXYCURL_API_KEY` | Contact enrichment | `.env` + `integrations/proxycurl_client.py` | ⏳ Pending |
| `GMAIL_CLIENT_ID` | Email OAuth | `.env` + `integrations/gmail_client.py` | ⏳ Pending |
| `GMAIL_CLIENT_SECRET` | Email OAuth | `.env` + `integrations/gmail_client.py` | ⏳ Pending |
| Supabase project URL + keys | Database + Auth | `.env` | ⏳ Pending |

> **Dev approach:** All integrations built with `USE_MOCK_DATA=true` and `MOCK_AGENTS=true`.
> When real keys are provided, flip both flags to `false` — no code changes needed.

### Deferred Technical Work
| Item | Reason Deferred | Target Version |
|------|----------------|----------------|
| Supabase Realtime push (instead of polling) | Polling is simpler for v1.0 | v1.5 |
| Rate limiting middleware (100 req/min/user) | Single user in v1.0 | v1.5 |
| Full analytics page (funnels, response rate charts) | Needs historical data to be useful | v1.5 |
| Agent prompt A/B testing framework | Overkill for single user | v2.0 |
| Celery Flower monitoring dashboard | Nice-to-have ops tooling | v1.5 |
| Multi-user RLS policy audit | Architecture is cohort-ready but untested at scale | v1.5 |
| Proxycurl rate limit queue (dedicated priority lane) | Low volume in v1.0 | v1.5 |
| SEC EDGAR full-text 8-K parsing | Regex-based extraction good enough for v1.0 | v1.5 |
| Dealroom integration | EU-focused, lower priority; NewsAPI covers initial needs | v1.5 |
| Email open/reply tracking (Gmail webhook) | Polling-based check sufficient for v1.0 | v1.5 |
| Production deployment (cloud hosting) | Docker local is sufficient for single user | v1.5 |
| Adversarial testing / red team (prompt injection) | Critical for multi-user; defer until v1.5 | v1.5 |
| PII redaction in agent memory/logs | Required for multi-user compliance | v1.5 |

### Known Technical Debt (Acceptable for v1.0)
- `USE_MOCK_DATA` flag is a dev shortcut — clean up mock routes before v1.5
- `signal_ids[]` on opportunities is a denormalized array — move to join table `opportunity_signals` in v1.5
- No structured logging format yet — add OpenTelemetry spans in v1.5
- No API versioning strategy beyond `/v1/` — define `/v2/` migration plan before v1.5
- `preferences_json` on users table is a grab-bag — normalize into proper columns in v1.5

---

## 12. Key Decisions Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-04-11 | FastAPI over Django | Async-first, better for agent/AI patterns |
| 2026-04-11 | Supabase over raw Postgres | Auth + RLS + realtime + pgvector in one |
| 2026-04-11 | Celery + Redis over cloud queue | Local dev simplicity, cost control |
| 2026-04-11 | Claude Sonnet for reasoning | Best reasoning quality for opportunity prediction |
| 2026-04-11 | Claude Haiku for classification | 10x cheaper, fast enough for signal labeling |
| 2026-04-11 | Next.js App Router | Server components for fast initial load |
| 2026-04-12 | Loveable FE as design reference | Index.tsx is the design baseline for all FE work |
| 2026-04-12 | Supabase Auth from day one (not hardcoded user) | Cohort-ready requirement; retrofitting auth is painful |
| 2026-04-12 | Both manual + cron signal ingestion | Manual for dev/testing; 4h cron for production |
| 2026-04-12 | Email: draft + confirm step (not auto-send) | User must approve before any send; safer product |
| 2026-04-12 | Analytics: dashboard stats only for v1.0 | Full funnels need historical data; defer to v1.5 |
| 2026-04-12 | Contact Identifier merged into Opportunity Predictor | Tightly coupled outputs; separate agent was unnecessary hop |
| 2026-04-12 | Career Fit Scorer + Positioning Advisor run in parallel | Both depend on Opportunity Predictor; neither depends on each other |
| 2026-04-12 | Mock mode via env flags (MOCK_AGENTS, USE_MOCK_DATA) | Full dev/test without API keys; flip flags when keys available |
| 2026-04-12 | agent_runs table for all AI invocations | Audit trail, cost tracking, debugging, prompt version rollback |
| 2026-04-12 | Signal source priority: NewsAPI + RSS + SEC EDGAR first | Free/low-cost; covers funding/exec/expansion signals adequately for v1.0 |

---

## 12. Git Branching Convention

Every phase lives on its own branch. No direct commits to `main`.

```bash
# Start a new phase
git checkout main && git pull origin main
git checkout -b phase/{N}-{short-name}
# e.g.  phase/2-core-backend-apis
#        phase/3-signal-intelligence
#        phase/4-ai-reasoning-layer

# Finish a phase
git push origin phase/{N}-{short-name}
# Open PR on GitHub → review → squash-merge → delete branch
```

| Branch | Purpose |
|--------|---------|
| `main` | Stable, always-deployable — merged phases only |
| `phase/{N}-{name}` | All work for Phase N (commits, sub-branches welcome) |

**Rule:** When a phase is declared complete, open a PR from `phase/{N}-{name}` → `main`, merge it, and delete the phase branch.

---

## 13. Day-to-Day Workflow

### Starting a Session
1. Read this file (CLAUDE.md) first
2. Read PLAN.md to know which phase you're in
3. Check `git status` and `git log --oneline -10`
4. If starting a new phase: `git checkout -b phase/{N}-{name}`
5. Run `/using-superpowers` to re-load skill context
6. Start work on the current phase

### Ending a Session
1. Commit all work with descriptive messages
2. Update PLAN.md — mark completed tasks ✅
3. Note any blockers or decisions made
4. Push to the current phase branch (not main)

### Finishing a Phase
1. Ensure all tasks are ✅ in PLAN.md
2. Run full test suite — 0 regressions
3. Open PR: `phase/{N}-{name}` → `main` on GitHub
4. Merge PR → delete phase branch

### When Stuck
1. Run `/systematic-debugging` skill
2. Check PLAN.md for the expected behavior
3. Check this file for architectural rules
4. Ask: Is this a frontend, backend, or integration issue?

---

## 13. Testing Strategy

| Layer | Tool | Coverage Target |
|-------|------|----------------|
| Unit (BE) | pytest + pytest-asyncio | 80% |
| Integration (BE) | pytest + httpx + real Supabase test DB | All API endpoints |
| Unit (FE) | Vitest + React Testing Library | 70% |
| E2E | Playwright | Golden paths for all 8 pages |
| AI Agent | Pytest + recorded fixtures | All agent prompts have snapshot tests |

---

## 14. Signal Sources Reference

| Source | Type | Update Frequency | What We Extract |
|--------|------|-----------------|----------------|
| NewsAPI | REST API | Real-time | Funding, M&A, expansion news |
| Crunchbase | REST API | Daily | Funding rounds, investor data, headcount |
| RSS Feeds | RSS/Atom | Hourly | Company blogs, press releases |
| SEC EDGAR | REST API | Daily | 8-K filings, major contracts, exec changes |
| Dealroom | REST API | Daily | European startup funding, investors |
| LinkedIn (via Proxycurl) | REST API | On-demand | Contact enrichment, job postings |

---

## 15. Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────┐
│                     APEX PLATFORM                        │
├─────────────────────────────────────────────────────────┤
│  SIGNAL LAYER                                            │
│  NewsAPI → Crunchbase → RSS → SEC → Dealroom             │
│       ↓ Celery Workers (async ingestion)                 │
│  Signal Storage (Supabase) ←→ Signal Classifier (Haiku)  │
├─────────────────────────────────────────────────────────┤
│  AI REASONING LAYER                                      │
│  Opportunity Predictor (Sonnet)                          │
│  Career Fit Scorer (Sonnet) ← Career Profile + Embeddings│
│  Action Generator (Sonnet)                               │
│  Email Drafter (Sonnet)                                  │
├─────────────────────────────────────────────────────────┤
│  DATA LAYER                                              │
│  Supabase Postgres (pgvector) + Redis (cache/queue)      │
│  Proxycurl → Company/Contact enrichment                  │
├─────────────────────────────────────────────────────────┤
│  API LAYER                                               │
│  FastAPI (async) — /api/v1/ — JWT Auth (Supabase)        │
├─────────────────────────────────────────────────────────┤
│  FRONTEND                                                │
│  Next.js 14 + Tailwind + shadcn/ui                       │
│  Dashboard | Signals | Opportunities | Actions           │
│  Outreach | Profile | Analytics | Settings               │
├─────────────────────────────────────────────────────────┤
│  EMAIL AUTOMATION                                        │
│  Gmail API (OAuth) → Drafts → Sends → Tracking           │
└─────────────────────────────────────────────────────────┘
```

---

*This file is the single source of truth. When in doubt, follow this file.*
