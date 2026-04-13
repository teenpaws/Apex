# Phase 9: Full Integration & E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire all systems together so real data flows from signal ingestion → classification → opportunity prediction → action generation → outreach. Remove all mock data fallbacks from the frontend.

**Architecture:** The backend is missing an `analytics` router and an `agents` router — both are referenced by the frontend but have TODO comments in `router.py`. Once those two routers are wired, the frontend already calls the correct endpoints for all 8 pages. The only frontend mock to remove is the `mockDashboardStats` fallback in `PipelineViz.tsx`.

**Tech Stack:** FastAPI (async), Pydantic v2, Next.js 14 App Router, React Query (TanStack), TypeScript

**Branch:** `phase/9-full-integration`

---

## CHECKPOINT SYSTEM — Resume Safety

Each task ends with a commit. If usage limits are hit mid-session, pick up from the last committed task by reading git log and continuing from the next unchecked task.

```bash
# To resume: find last commit, start from next task
git log --oneline -15
```

---

## BE AGENT TASKS (backend/)

### Task BE-1: Create analytics router

**Files:**
- Create: `backend/app/api/v1/analytics.py`
- Modify: `backend/app/api/v1/router.py` (register analytics router)
- Create: `backend/app/api/mock_responses/analytics.json`

**Context:** The frontend calls `GET /api/v1/analytics/dashboard` (in `useDashboardStats` hook and `analyticsPage`) and `GET /api/v1/analytics/costs`. Neither endpoint exists yet — `router.py` has `# TODO: include analytics router (Phase 4)`.

The `DashboardStats` TypeScript type (used by frontend) expects:
```json
{
  "signals_this_week": 12,
  "new_opportunities": 4,
  "actions_completed": 3,
  "pipeline_stages": {
    "signals": 12,
    "opportunities": 4,
    "actions": 5,
    "outreach": 2
  }
}
```

- [ ] **Step 1: Create mock response file**

Create `backend/app/api/mock_responses/analytics.json`:
```json
{
  "signals_this_week": 12,
  "new_opportunities": 4,
  "actions_completed": 3,
  "pipeline_stages": {
    "signals": 12,
    "opportunities": 4,
    "actions": 5,
    "outreach": 2
  }
}
```

- [ ] **Step 2: Create the analytics router**

Create `backend/app/api/v1/analytics.py`:
```python
"""
Analytics API routes — dashboard stats and agent cost endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.db.session import get_db_client
from pydantic import BaseModel

router = APIRouter(prefix="/analytics", tags=["analytics"])

MOCK_DIR = Path(__file__).parent.parent / "mock_responses"


class PipelineStages(BaseModel):
    signals: int
    opportunities: int
    actions: int
    outreach: int


class DashboardStats(BaseModel):
    signals_this_week: int
    new_opportunities: int
    actions_completed: int
    pipeline_stages: PipelineStages


class CostEntry(BaseModel):
    agent_name: str
    calls: int
    total_tokens: int
    cost_usd: float


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
) -> DashboardStats:
    """Return real-time dashboard statistics for the authenticated user."""
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        data = json.loads((MOCK_DIR / "analytics.json").read_text())
        return DashboardStats(**data)

    db = get_db_client()
    user_id = current_user["id"]

    from datetime import datetime, timedelta, timezone
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Count signals this week
    sig_res = (
        db.table("signals")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("signal_date", week_ago[:10])
        .execute()
    )
    signals_this_week = sig_res.count or 0

    # Count new opportunities (created this week)
    opp_res = (
        db.table("opportunities")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", week_ago)
        .execute()
    )
    new_opportunities = opp_res.count or 0

    # Count actions completed (status=DONE)
    act_done_res = (
        db.table("actions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("status", "DONE")
        .execute()
    )
    actions_completed = act_done_res.count or 0

    # Pipeline stage totals (all-time counts)
    sig_total = (
        db.table("signals")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    opp_total = (
        db.table("opportunities")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    act_total = (
        db.table("actions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    out_total = (
        db.table("outreach_emails")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )

    return DashboardStats(
        signals_this_week=signals_this_week,
        new_opportunities=new_opportunities,
        actions_completed=actions_completed,
        pipeline_stages=PipelineStages(
            signals=sig_total.count or 0,
            opportunities=opp_total.count or 0,
            actions=act_total.count or 0,
            outreach=out_total.count or 0,
        ),
    )


@router.get("/costs", response_model=list[CostEntry])
async def get_agent_costs(
    date_from: str | None = Query(None, description="ISO date string (inclusive)"),
    date_to: str | None = Query(None, description="ISO date string (inclusive)"),
    current_user: dict = Depends(get_current_user),
) -> list[CostEntry]:
    """Return agent cost breakdown by agent_name for the authenticated user."""
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        return []

    db = get_db_client()
    user_id = current_user["id"]

    query = db.table("agent_runs").select("*").eq("user_id", user_id)
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", date_to)

    res = query.execute()
    rows = res.data or []

    # Aggregate by agent_name
    agg: dict[str, CostEntry] = {}
    for row in rows:
        name = row["agent_name"]
        if name not in agg:
            agg[name] = CostEntry(
                agent_name=name, calls=0, total_tokens=0, cost_usd=0.0
            )
        agg[name].calls += 1
        agg[name].total_tokens += (row.get("tokens_in") or 0) + (row.get("tokens_out") or 0)
        agg[name].cost_usd += row.get("cost_usd") or 0.0

    return sorted(agg.values(), key=lambda e: e.cost_usd, reverse=True)
```

- [ ] **Step 3: Register analytics router in router.py**

In `backend/app/api/v1/router.py`, replace the TODO comment block at the bottom:
```python
# Before (remove this):
# ── Remaining routers ─────────────────────────────────────────────────────────
# TODO: include agents router        (Phase 2)
# TODO: include analytics router     (Phase 4)

# After (add this):
from app.api.v1.analytics import router as analytics_router
from app.api.v1.agents import router as agents_router

# ── Phase 9: Analytics + Agent Status ─────────────────────────────────────────
router.include_router(analytics_router)
router.include_router(agents_router)
```

Note: Do this AFTER Task BE-2 creates `agents.py`, or temporarily import only analytics first.

- [ ] **Step 4: Run the backend and test the endpoint manually**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
# In another terminal:
curl -s http://localhost:8000/api/v1/analytics/dashboard | python -m json.tool
# Expected (USE_MOCK_DATA=True): {"signals_this_week": 12, ...}
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/analytics.py backend/app/api/mock_responses/analytics.json
git commit -m "feat(phase-9): add analytics router — GET /analytics/dashboard + /analytics/costs"
```

---

### Task BE-2: Create agents router (run-status + runs)

**Files:**
- Create: `backend/app/api/v1/agents.py`
- Modify: `backend/app/api/v1/router.py` (register agents router — do this after BE-1 and BE-2)

**Context:** The frontend calls:
- `GET /api/v1/agents/run-status/{run_id}` — polls task status
- `GET /api/v1/agents/runs` — lists all agent run history (used by analytics page)

The `AgentRun` TypeScript type expects: `{ id, agent_name, model_used, tokens_in, tokens_out, cost_usd, duration_ms, status, created_at }`

- [ ] **Step 1: Create the agents router**

Create `backend/app/api/v1/agents.py`:
```python
"""
Agents API routes — run status polling and run history.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.db.session import get_db_client
from pydantic import BaseModel

router = APIRouter(prefix="/agents", tags=["agents"])


class RunStatus(BaseModel):
    run_id: str
    status: str          # queued | running | SUCCESS | FAILED
    progress: int = 0    # 0–100
    result_id: str | None = None
    error_message: str | None = None


class AgentRunRead(BaseModel):
    id: str
    agent_name: str
    model_used: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_ms: int
    status: str
    error_message: str | None = None
    created_at: str


@router.get("/run-status/{run_id}", response_model=RunStatus)
async def get_run_status(
    run_id: str,
    current_user: dict = Depends(get_current_user),
) -> RunStatus:
    """Poll the status of a background agent run (Celery task or agent_run record)."""
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        # In mock mode, immediately return SUCCESS so FE polling terminates
        return RunStatus(run_id=run_id, status="SUCCESS", progress=100)

    db = get_db_client()
    user_id = current_user["id"]

    res = (
        db.table("agent_runs")
        .select("*")
        .eq("id", run_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Run not found")

    row = res.data
    return RunStatus(
        run_id=run_id,
        status=row["status"],
        progress=100 if row["status"] in ("SUCCESS", "FAILED") else 50,
        result_id=row.get("id"),
        error_message=row.get("error_message"),
    )


@router.get("/runs", response_model=list[AgentRunRead])
async def list_agent_runs(
    current_user: dict = Depends(get_current_user),
) -> list[AgentRunRead]:
    """List recent agent runs for the authenticated user (newest first, max 100)."""
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        return []

    db = get_db_client()
    user_id = current_user["id"]

    res = (
        db.table("agent_runs")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    rows = res.data or []
    return [AgentRunRead(**r) for r in rows]
```

- [ ] **Step 2: Register both new routers in router.py**

Open `backend/app/api/v1/router.py` and replace the TODO block at the bottom with:
```python
from app.api.v1.analytics import router as analytics_router
from app.api.v1.agents import router as agents_router

# ── Phase 9: Analytics + Agent Status ─────────────────────────────────────────
router.include_router(analytics_router)
router.include_router(agents_router)
```

- [ ] **Step 3: Test both new endpoints**

```bash
# analytics/dashboard
curl -s http://localhost:8000/api/v1/analytics/dashboard | python -m json.tool
# Expected: {"signals_this_week": 12, "new_opportunities": 4, ...}

# agents/runs (empty list in mock mode)
curl -s http://localhost:8000/api/v1/agents/runs | python -m json.tool
# Expected: []

# agents/run-status (mock immediately returns SUCCESS)
curl -s http://localhost:8000/api/v1/agents/run-status/test-run-123 | python -m json.tool
# Expected: {"run_id": "test-run-123", "status": "SUCCESS", "progress": 100, ...}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/agents.py backend/app/api/v1/router.py
git commit -m "feat(phase-9): add agents router — GET /agents/runs + /agents/run-status/{id}"
```

---

### Task BE-3: Verify full pipeline end-to-end (mock mode)

**Files:** No new files — integration test using existing endpoints.

**Context:** The pipeline is: `POST /signals/ingest` → Celery worker classifies → opportunity predicted → action generated. We need to verify the full chain works without errors, using `USE_MOCK_DATA=True` and `MOCK_AGENTS=True`.

- [ ] **Step 1: Start the backend server**

```bash
cd backend
# Ensure .env has USE_MOCK_DATA=true and MOCK_AGENTS=true
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Hit all endpoints and verify 200 responses**

```bash
# Health
curl -s http://localhost:8000/api/v1/health | python -m json.tool

# Signals list
curl -s "http://localhost:8000/api/v1/signals" | python -m json.tool

# Opportunities list
curl -s "http://localhost:8000/api/v1/opportunities" | python -m json.tool

# Actions list
curl -s "http://localhost:8000/api/v1/actions" | python -m json.tool

# Profile
curl -s "http://localhost:8000/api/v1/profile" | python -m json.tool

# Outreach list
curl -s "http://localhost:8000/api/v1/outreach" | python -m json.tool

# Analytics dashboard (NEW — just added)
curl -s "http://localhost:8000/api/v1/analytics/dashboard" | python -m json.tool

# Agent runs (NEW — just added)
curl -s "http://localhost:8000/api/v1/agents/runs" | python -m json.tool
```

All must return HTTP 200. Note any 404, 422, or 500 errors and fix them before moving on.

- [ ] **Step 3: Trigger signal ingest and verify mock pipeline**

```bash
curl -s -X POST http://localhost:8000/api/v1/signals/ingest | python -m json.tool
# Expected: {"run_id": "...", "status": "queued", "message": "Processing started"}

# Poll run-status until SUCCESS
curl -s "http://localhost:8000/api/v1/agents/run-status/<run_id_from_above>" | python -m json.tool
```

- [ ] **Step 4: Fix any bugs found during Step 2/3**

Common issues to look for:
- Missing auth header → check `get_current_user` in `app/core/dependencies.py` (in mock mode it should not require a real JWT)
- 422 Unprocessable Entity → check request body schemas match Pydantic models
- 500 Internal Server Error → read the traceback in the uvicorn log

- [ ] **Step 5: Commit after all endpoints return 200**

```bash
git add -p  # stage only integration-fix changes
git commit -m "fix(phase-9): resolve integration bugs — all BE endpoints return 200 in mock mode"
```

---

### Task BE-4: Verify response shapes match frontend TypeScript types

**Files:**
- Read: `frontend/types/index.ts` (or wherever types live — check `frontend/types/`)
- Fix any mismatches in BE response models

**Context:** The frontend React Query hooks parse API responses and cast them to TypeScript types. If a field name or type differs between BE and FE, the UI will silently show `undefined`. This task closes that gap.

- [ ] **Step 1: Read the frontend types file**

```bash
cat frontend/types/index.ts
# (or find the correct path):
find frontend -name "*.ts" -path "*/types*" | grep -v node_modules
```

- [ ] **Step 2: Cross-reference each type against its BE response model**

For each entity, compare the FE TypeScript interface to the BE Pydantic model:

| Entity | FE type file | BE model file |
|--------|-------------|---------------|
| Signal | `types/index.ts` | `app/models/signal.py` (SignalRead) |
| Opportunity | `types/index.ts` | `app/models/opportunity.py` (OpportunityRead) |
| Action | `types/index.ts` | `app/models/action.py` (ActionRead) |
| OutreachEmail | `types/index.ts` | `app/models/outreach.py` (OutreachEmailRead) |
| DashboardStats | `types/index.ts` | `app/api/v1/analytics.py` (DashboardStats) |
| AgentRun | `types/index.ts` | `app/api/v1/agents.py` (AgentRunRead) |

Note any field that appears in FE type but is missing from the BE response, or is named differently (e.g. FE uses `company` but BE returns `company_name`).

- [ ] **Step 3: Fix mismatches in BE response models**

If BE Pydantic models are missing fields that the FE expects, add them as `Optional` with `None` defaults. Never change FE types to accommodate a broken BE response — fix the BE to match the contract.

Example fix pattern:
```python
# In app/models/signal.py, if FE needs 'company' field:
class SignalRead(BaseModel):
    # ... existing fields ...
    company: str | None = None        # FE alias for company name
    date: str | None = None           # FE alias for relative date string
    linkedOpportunityIds: list[str] = []  # FE camelCase alias
```

- [ ] **Step 4: Verify signals endpoint returns `data` array wrapper**

The FE `useSignals` hook expects `PaginatedResponse<Signal>` shape:
```json
{
  "data": [...],
  "total": N,
  "page": 1,
  "page_size": 20
}
```

But `signals.py` returns `PaginatedSignalsResponse` with `signals` not `data`.
Check `app/api/v1/signals.py` — if the key is `signals`, the FE hook (which does `body.data.map(...)`) will receive `undefined`.

Fix if needed: in `signals.py`, rename `signals` field to `data` in `PaginatedSignalsResponse`:
```python
class PaginatedSignalsResponse(BaseModel):
    data: list[SignalRead]   # was: signals
    total: int
    page: int
    page_size: int
```

Do the same check for opportunities and actions paginated responses.

- [ ] **Step 5: Commit**

```bash
git add backend/app/
git commit -m "fix(phase-9): align BE response field names with FE TypeScript type contract"
```

---

## FE AGENT TASKS (frontend/)

### Task FE-1: Remove mockDashboardStats from PipelineViz

**Files:**
- Modify: `frontend/components/shared/PipelineViz.tsx`

**Context:** `PipelineViz.tsx` currently falls back to `mockDashboardStats` from `@/lib/mock` when `stats` is null:
```tsx
const { pipeline_stages } = stats ?? mockDashboardStats;
```
This means mock data shows even when the real API is available. The fix: show zero counts while loading, and render nothing different once data arrives — the parent (`DashboardPage`) already handles the loading state via `useDashboardStats()`.

- [ ] **Step 1: Edit PipelineViz.tsx to remove the mock import and fallback**

Open `frontend/components/shared/PipelineViz.tsx`. Replace the full file content with:

```tsx
'use client';

import { ArrowRight } from 'lucide-react';
import type { DashboardStats } from '@/types';

const stages = [
  { key: 'signals',       label: 'Signals',       color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  { key: 'opportunities', label: 'Opportunities', color: 'bg-violet-500/20 text-violet-400 border-violet-500/30' },
  { key: 'actions',       label: 'Actions',       color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  { key: 'outreach',      label: 'Outreach',      color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
] as const;

const EMPTY_STAGES: DashboardStats['pipeline_stages'] = {
  signals: 0,
  opportunities: 0,
  actions: 0,
  outreach: 0,
};

interface PipelineVizProps {
  stats?: DashboardStats | null;
}

export function PipelineViz({ stats }: PipelineVizProps) {
  const pipeline_stages = stats?.pipeline_stages ?? EMPTY_STAGES;

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="text-xs text-muted-foreground mb-4 font-medium uppercase tracking-wider">
        Pipeline Overview
      </p>
      <div className="flex items-center gap-2">
        {stages.map((stage, idx) => (
          <div key={stage.key} className="flex items-center gap-2 flex-1">
            <div
              className={`flex-1 rounded-lg border px-4 py-3 text-center ${stage.color}`}
            >
              <p className="text-lg font-bold">
                {pipeline_stages[stage.key]}
              </p>
              <p className="text-[10px] mt-0.5 opacity-80">{stage.label}</p>
            </div>
            {idx < stages.length - 1 && (
              <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles without errors**

```bash
cd frontend
npx tsc --noEmit 2>&1 | head -40
```

Expected: no errors. If `DashboardStats['pipeline_stages']` causes a type error, check `frontend/types/index.ts` to see the exact shape of `pipeline_stages`.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/shared/PipelineViz.tsx
git commit -m "fix(phase-9): remove mockDashboardStats fallback from PipelineViz — show zeros while loading"
```

---

### Task FE-2: Verify all hooks call real APIs (no mock imports in hooks or pages)

**Files:**
- Read: all files in `frontend/hooks/`
- Read: all files in `frontend/app/(dashboard)/`
- Fix any remaining `@/lib/mock` imports in pages

**Context:** The `lib/mock/index.ts` file contains all mock data. We need to confirm no page or hook still imports from it (except possibly as a genuine dev-only fallback that is clearly isolated).

- [ ] **Step 1: Grep for remaining mock imports**

```bash
cd frontend
grep -rn "from '@/lib/mock'" . --include="*.tsx" --include="*.ts" | grep -v node_modules | grep -v "__tests__"
```

If no output: all mock imports are removed. Skip to Step 4 (commit).
If there are results: proceed to Step 2.

- [ ] **Step 2: For each file importing from @/lib/mock, remove the import and use real API data**

Common pattern to fix:
```tsx
// BEFORE (bad):
import { mockDashboardStats } from '@/lib/mock';
const stats = realStats ?? mockDashboardStats;

// AFTER (good):
// No mock import. Use undefined/null when data isn't loaded.
const stats = realStats ?? null;
// In JSX: render a loading skeleton or empty state instead of mock data
```

- [ ] **Step 3: After removing each mock import, run TypeScript check**

```bash
npx tsc --noEmit 2>&1 | head -40
```

Fix any type errors introduced by removing mock data.

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "fix(phase-9): remove all @/lib/mock imports from pages and hooks"
```

---

### Task FE-3: Verify all 8 pages load without console errors

**Files:** No code changes — verification only.

**Context:** With the BE running in mock mode and FE calling real endpoints, all 8 pages must load cleanly. If there are API 404s or shape mismatches, the FE will show the `ErrorState` component. We need to verify each page, capture any errors, and fix them.

- [ ] **Step 1: Start the backend in mock mode**

```bash
cd backend
# Ensure .env: USE_MOCK_DATA=true, MOCK_AGENTS=true
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: Start the frontend**

```bash
cd frontend
npm run dev
# Frontend on http://localhost:3000
```

- [ ] **Step 3: Visit each page and check for ErrorState components or console errors**

Open browser to `http://localhost:3000`. Visit each route:
1. `/` — Dashboard
2. `/signals`
3. `/opportunities`
4. `/actions`
5. `/outreach`
6. `/profile`
7. `/analytics`
8. `/settings`

For each page, open browser DevTools → Console. Note any:
- Red errors (API call failures, 404s, 500s)
- `undefined` values where numbers/strings are expected
- React warnings about missing keys or type mismatches

- [ ] **Step 4: Fix each error found**

For API 404s: the endpoint is missing — add it to the appropriate router.
For shape mismatches (e.g., `undefined` in a field): fix the BE response model (Task BE-4 may have missed some).
For React key warnings: add `key` props.

- [ ] **Step 5: Commit after all 8 pages load cleanly**

```bash
git add -p
git commit -m "fix(phase-9): fix all FE page errors — all 8 routes load without console errors"
```

---

### Task FE-4: Wire analytics page to real data (remove hardcoded MOCK_STATS fallback)

**Files:**
- Modify: `frontend/app/(dashboard)/analytics/page.tsx`

**Context:** The analytics page has `const stats: DashboardStats = statsQuery.data ?? MOCK_STATS;` — this falls back to `MOCK_STATS` when the API hasn't returned yet. Now that `GET /analytics/dashboard` is implemented, the fallback should show a loading skeleton, not mock data. The chart data (`MOCK_SIGNAL_VELOCITY`, `MOCK_COMPANY_SIGNALS`) is intentionally kept as visual examples until real historical data exists (per PLAN.md deferred items) but should be labeled clearly as sample data (already done).

- [ ] **Step 1: Remove MOCK_STATS constant and update stats usage**

In `frontend/app/(dashboard)/analytics/page.tsx`, find and remove the `MOCK_STATS` constant:
```tsx
// Remove this block entirely:
const MOCK_STATS: DashboardStats = {
  signals_this_week: 24,
  new_opportunities: 7,
  actions_completed: 12,
  pipeline_stages: { signals: 142, opportunities: 38, actions: 21, outreach: 5 },
};
```

Then update the `AnalyticsPage` component to handle the loading state properly:
```tsx
export default function AnalyticsPage() {
  const statsQuery = useDashboardStats();
  const runsQuery = useAgentRuns();

  // stats may be undefined while loading — StatCards handle null gracefully
  const stats = statsQuery.data;
  const runs: AgentRun[] = runsQuery.data ?? [];
  const costRows = useMemo(() => buildCostRows(runs), [runs]);

  const totalCostThisMonth = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(1);
    cutoff.setHours(0, 0, 0, 0);
    return runs
      .filter((r) => new Date(r.created_at) >= cutoff)
      .reduce((sum, r) => sum + r.cost_usd, 0);
  }, [runs]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Activity className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold text-foreground">Analytics</h1>
      </div>

      {/* Stat cards row */}
      {statsQuery.isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} lines={1} />)}
        </div>
      ) : statsQuery.isError ? (
        <ErrorState error={statsQuery.error as Error} onRetry={() => statsQuery.refetch()} />
      ) : stats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Signals this week"
            value={stats.signals_this_week}
            icon={<Zap className="h-4 w-4" />}
            accent="text-violet-400"
          />
          <StatCard
            label="New opportunities"
            value={stats.new_opportunities}
            icon={<TrendingUp className="h-4 w-4" />}
            accent="text-emerald-400"
          />
          <StatCard
            label="Actions completed"
            value={stats.actions_completed}
            icon={<CheckSquare className="h-4 w-4" />}
            accent="text-blue-400"
          />
          <StatCard
            label="Agent cost this month"
            value={`$${totalCostThisMonth.toFixed(4)}`}
            icon={<DollarSign className="h-4 w-4" />}
            accent="text-amber-400"
          />
        </div>
      ) : null}

      {/* Pipeline funnel — only render when stats available */}
      {stats && (
        <Card className="p-5 bg-card border-border">
          <h2 className="text-sm font-semibold text-foreground mb-4">
            Conversion Pipeline
          </h2>
          <PipelineFunnel stages={stats.pipeline_stages} />
        </Card>
      )}

      {/* Charts and agent cost table remain unchanged below */}
      {/* ... rest of the existing JSX ... */}
    </div>
  );
}
```

- [ ] **Step 2: Import ErrorState if not already imported**

Check top of `analytics/page.tsx` — add if missing:
```tsx
import { ErrorState } from '@/components/shared/ErrorState';
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend
npx tsc --noEmit 2>&1 | head -40
```

Fix any type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(dashboard\)/analytics/page.tsx
git commit -m "fix(phase-9): analytics page — remove MOCK_STATS fallback, use real API data with loading states"
```

---

## FINAL STEPS (after both BE and FE tasks complete)

### Task FINAL-1: Run full integration smoke test

- [ ] Start backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- [ ] Start frontend: `cd frontend && npm run dev`
- [ ] Visit all 8 pages — verify no console errors, no ErrorState shown
- [ ] Trigger signal ingest via dashboard or API: `curl -X POST http://localhost:8000/api/v1/signals/ingest`
- [ ] Confirm analytics/dashboard returns real-looking data (mock data in mock mode is correct)
- [ ] Commit any final fixes

### Task FINAL-2: Update PLAN.md

- [ ] Mark Phase 9 Sprint 9.1 BE and FE tasks as ✅ in PLAN.md
- [ ] Note that QA tasks (Playwright E2E) are deferred to next session
- [ ] Commit: `git commit -m "chore: Phase 9 BE+FE complete — mark sprint 9.1 tasks done, QA pending"`

---

## Resumability Guide

If usage limits are hit, the next session should:

1. Read `git log --oneline -15` to find the last completed task
2. Open this plan file at `docs/superpowers/plans/2026-04-13-phase9-full-integration.md`
3. Find the first unchecked `- [ ]` checkbox after the last committed task
4. Continue from that task

The git branch is `phase/9-full-integration`. All intermediate commits use the prefix `feat(phase-9):` or `fix(phase-9):` for easy identification.

```bash
# Quick resume command sequence:
git log --oneline -15
# Find last phase-9 commit → identify next task → continue
```
