---
phase: "1"
plan: "2"
subsystem: "database"
tags: [database, schema, migrations, orm, pydantic, sqlalchemy, pgvector, rls, seed-data]
dependency_graph:
  requires: ["1-1"]
  provides: ["db-schema", "orm-models", "pydantic-schemas", "db-session", "seed-data"]
  affects: ["all-future-backend-plans"]
tech_stack:
  added: ["pgvector==0.3.6", "sqlalchemy[asyncio]"]
  patterns: ["lazy-engine-init", "pydantic-v2-from-attributes", "rls-auth-uid", "ivfflat-vector-index"]
key_files:
  created:
    - backend/app/db/migrations/002_create_users.sql
    - backend/app/db/migrations/003_create_companies.sql
    - backend/app/db/migrations/004_create_contacts.sql
    - backend/app/db/migrations/005_create_career_profiles.sql
    - backend/app/db/migrations/006_create_signals.sql
    - backend/app/db/migrations/007_create_opportunities.sql
    - backend/app/db/migrations/008_create_actions.sql
    - backend/app/db/migrations/009_create_outreach_emails.sql
    - backend/app/db/migrations/010_create_agent_runs.sql
    - backend/app/db/migrations/011_create_rls_policies.sql
    - backend/app/db/migrations/012_create_indexes.sql
    - backend/app/models/enums.py
    - backend/app/models/base.py
    - backend/app/models/user.py
    - backend/app/models/company.py
    - backend/app/models/signal.py
    - backend/app/models/opportunity.py
    - backend/app/models/action.py
    - backend/app/models/outreach.py
    - backend/app/models/agent_run.py
    - backend/app/db/session.py
    - backend/app/db/seeds/seed_dev.py
    - backend/app/db/seeds/__init__.py
    - backend/tests/integration/test_db.py
  modified:
    - backend/app/models/__init__.py
    - backend/requirements.txt
decisions:
  - "Lazy engine init in session.py avoids asyncpg ImportError in mock mode (Python 3.14 wheel unavailable)"
  - "pgvector imported conditionally (try/except) so models remain importable without the package installed"
  - "agent_runs RLS has no UPDATE policy — audit trail is immutable by design"
  - "Seed data uses fixed UUIDs for reproducibility across dev runs"
  - "IVFFlat indexes use lists=100 (tunable at scale to sqrt(row_count))"
metrics:
  duration: "~18 minutes"
  completed: "2026-04-12"
  tasks_completed: 8
  files_created: 24
  files_modified: 2
---

# Phase 1 Plan 2: Database Schema Summary

Full database layer for Apex platform — 11 SQL migrations (9 tables + RLS + indexes), 9 SQLAlchemy ORM models with Pydantic v2 schemas, async DB session with lazy initialization, dev seed data script, and integration tests structured for live Supabase.

## What Was Built

### SQL Migrations (11 files, ready for Supabase SQL editor)

| Migration | Table | Notes |
|-----------|-------|-------|
| 001 | (extensions) | Pre-existing — vector + uuid-ossp |
| 002 | users | Core accounts; mirrors Supabase Auth |
| 003 | companies | Shared company profiles; no user_id (not RLS scoped) |
| 004 | contacts | Proxycurl-enriched people; linked to companies |
| 005 | career_profiles | Aspirations + target roles + vector(1536) embedding |
| 006 | signals | Market intelligence events + dedup_hash UNIQUE + vector(1536) |
| 007 | opportunities | AI-predicted roles; signal_ids uuid[] (denormalized for v1.0) |
| 008 | actions | User task queue; priority/status enums |
| 009 | outreach_emails | Email drafts + Gmail message tracking |
| 010 | agent_runs | Immutable AI audit trail |
| 011 | (RLS policies) | `user_id = auth.uid()` on all 7 user-scoped tables; agent_runs: no UPDATE |
| 012 | (indexes) | B-tree indexes + IVFFlat (lists=100) on both embedding columns |

### Python Enums (enums.py)
`SignalType`, `Confidence`, `OpportunityStatus`, `ActionType`, `Priority`, `ActionStatus`, `AgentRunStatus` — all as `str, enum.Enum` for Pydantic/SQLAlchemy compatibility.

### ORM Models + Pydantic Schemas (7 model files)
Each file provides: `XxxORM` (SQLAlchemy mapped class), `XxxCreate`, `XxxRead`, `XxxUpdate` (Pydantic v2 with `model_config = ConfigDict(from_attributes=True)`).

### DB Session (session.py)
- Lazy `create_async_engine` — engine only created on first DB call, not at import time
- `get_db()` async generator for FastAPI `Depends()` injection
- `get_supabase_client()` returns `None` gracefully when credentials are placeholders
- asyncpg driver: `postgresql://` → `postgresql+asyncpg://` URL conversion

### Seed Data (seed_dev.py)
- 1 user (`test@apex.dev`, UUID `00000000-0000-0000-0000-000000000001`)
- 5 companies: Mistral AI, McKinsey, Dataiku, Contentsquare, Ledger
- 10 signals: mix of FUNDING, EXEC_HIRE, EXPANSION, JOB_POSTING_PATTERN, CONTRACT
- 3 opportunities: HIGH/MEDIUM/SPECULATIVE confidence with realistic Paris MBA framing
- 5 actions: TODO/IN_PROGRESS/DONE/SNOOZED states
- `--dry-run` flag prints all SQL + params without executing
- `ON CONFLICT DO NOTHING` makes re-runs idempotent

### Integration Tests (test_db.py)
7 tests, all `@pytest.mark.skipif(settings.USE_MOCK_DATA)` — skipped in dev, run against live Supabase:
- `test_tables_exist`, `test_rls_enabled`, `test_career_profiles_has_embedding`, `test_signals_has_embedding`, `test_signals_dedup_hash_unique`, `test_seed_data_loads`, `test_agent_runs_no_update_policy`

## Verification Results

```
python -c "from app.models import *; print('Models import OK')"
# Models import OK

python -m pytest tests/ -v
# 5 passed (health + config), 7 skipped (DB integration, USE_MOCK_DATA=true)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lazy engine initialization to fix asyncpg ImportError**
- **Found during:** Task 5 (DB session)
- **Issue:** `create_async_engine()` at module level fails immediately when `asyncpg` is not installed (Python 3.14 wheel unavailable — noted in existing requirements.txt). Import-time failure would break all model imports.
- **Fix:** Moved engine creation into `_get_engine()` factory function called lazily on first DB use. The `get_db()` and `get_supabase_client()` remain importable without asyncpg present.
- **Files modified:** `backend/app/db/session.py`
- **Commit:** 3ffbd2b

## Known Stubs

None — all model files wire real column definitions. Seed data uses realistic (non-placeholder) content. No TODO/FIXME stubs in produced files.

## To Activate (When Supabase Credentials Arrive)

1. Run migrations 001–012 in Supabase SQL editor in order
2. Set `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` in `.env`
3. Set `USE_MOCK_DATA=false` in `.env`
4. Run `python -m app.db.seeds.seed_dev` (live mode) to populate dev data
5. Run `pytest tests/integration/test_db.py -v` — all 7 should pass

## Self-Check: PASSED

Files verified:
- backend/app/db/migrations/ (11 files) — FOUND
- backend/app/models/enums.py — FOUND
- backend/app/models/base.py — FOUND
- backend/app/models/user.py, company.py, signal.py, opportunity.py, action.py, outreach.py, agent_run.py — FOUND
- backend/app/db/session.py — FOUND
- backend/app/db/seeds/seed_dev.py — FOUND
- backend/tests/integration/test_db.py — FOUND

Commits verified:
- 66f0f08: SQL migrations 002-012
- 9d495a3: ORM models + Pydantic schemas
- 3ffbd2b: DB session (lazy engine)
- 5c3dd81: Seed data script
- f75c8c6: Integration tests
- 40bfd9f: requirements.txt update
