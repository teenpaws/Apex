# CLAUDE.md — Apex Platform: The Holy Grail Dev Reference

> **This file is the single source of truth for all development on the Apex platform.**
> Read this before starting any session. Update it when decisions change.
> Last updated: 2026-04-12

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
           enrichment_json, last_enriched_at
contacts: id, company_id, name, title, linkedin_url, email,
          enrichment_json (Proxycurl), last_enriched_at
```

**Signals** (market intelligence raw data)
```
signals: id, user_id, company_id, type (enum), source, title, 
         description, raw_data_json, signal_date, 
         relevance_score float, processed_at, embedding vector[1536]
         
signal_types: FUNDING | EXEC_HIRE | EXPANSION | LAYOFF | 
              JOB_POSTING_PATTERN | MA | CONTRACT | EARNINGS
```

**Opportunities** (predicted roles — AI-generated)
```
opportunities: id, user_id, company_id, predicted_role, 
               confidence (HIGH/MEDIUM/SPECULATIVE),
               timeline_weeks int, why_fit text, 
               positioning_notes text, predicted_salary_range,
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
                 sent_at, gmail_message_id, opened_at, replied_at
```

---

## 5. Agent Architecture

### Agent Types
| Agent | Model | Responsibility |
|-------|-------|----------------|
| Signal Classifier | Claude Haiku | Classify raw signals into types, score relevance (fast, cheap) |
| Opportunity Predictor | Claude Sonnet | Analyze signals → predict hiring needs + timeline |
| Career Fit Scorer | Claude Sonnet | Score how well user's profile fits a predicted opportunity |
| Positioning Advisor | Claude Sonnet | Generate positioning narrative for user → company |
| Contact Identifier | Claude Sonnet | Identify best contact to approach at a company |
| Email Drafter | Claude Sonnet | Draft personalized outreach emails |
| Action Generator | Claude Sonnet | Convert opportunities → prioritized action items |

### Agent Orchestration Pattern
```
Signal Ingestion (Celery) 
  → Signal Classifier (Haiku) — classify + score
  → Opportunity Predictor (Sonnet) — predict roles
  → Career Fit Scorer (Sonnet) — score user fit
  → Action Generator (Sonnet) — create actions
  → Email Drafter (Sonnet) — draft outreach [on demand]
```

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

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/signals` | List signals (paginated, filterable) |
| GET | `/signals/{id}` | Signal detail |
| POST | `/signals/ingest` | Trigger manual signal ingest |
| GET | `/opportunities` | List predicted opportunities |
| GET | `/opportunities/{id}` | Opportunity detail |
| POST | `/opportunities/{id}/refresh` | Re-score with latest signals |
| GET | `/actions` | List actions (filterable by status/priority) |
| PUT | `/actions/{id}` | Update action status |
| POST | `/actions/{id}/draft-email` | Generate email draft for action |
| GET | `/outreach` | List outreach emails |
| POST | `/outreach/{id}/send` | Send via Gmail |
| GET | `/profile` | Get career profile |
| PUT | `/profile` | Update career profile |
| POST | `/profile/analyze` | Trigger profile re-analysis |
| GET | `/companies/{id}` | Company detail + signals |
| GET | `/analytics/dashboard` | Dashboard stats |
| POST | `/auth/login` | Supabase auth |

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

## 11. Key Decisions Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-04-11 | FastAPI over Django | Async-first, better for agent/AI patterns |
| 2026-04-11 | Supabase over raw Postgres | Auth + RLS + realtime + pgvector in one |
| 2026-04-11 | Celery + Redis over cloud queue | Local dev simplicity, cost control |
| 2026-04-11 | Claude Sonnet for reasoning | Best reasoning quality for opportunity prediction |
| 2026-04-11 | Claude Haiku for classification | 10x cheaper, fast enough for signal labeling |
| 2026-04-11 | Next.js App Router | Server components for fast initial load |
| 2026-04-12 | Loveable FE as design reference | Index.tsx is the design baseline for all FE work |

---

## 12. Day-to-Day Workflow

### Starting a Session
1. Read this file (CLAUDE.md) first
2. Read PLAN.md to know which phase you're in
3. Check `git status` and `git log --oneline -10`
4. Run `/using-superpowers` to re-load skill context
5. Start work on the current phase

### Ending a Session
1. Commit all work with descriptive messages
2. Update PLAN.md — mark completed tasks ✅
3. Note any blockers or decisions made
4. Push to remote branch

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
