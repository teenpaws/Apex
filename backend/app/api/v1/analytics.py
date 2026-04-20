"""Analytics API routes — dashboard stats and agent cost endpoints."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.dependencies import get_current_user
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

    import asyncpg
    import uuid as _uuid
    from app.db.session import get_asyncpg_db_url
    user_id = current_user["id"]
    uid = _uuid.UUID(user_id)

    db_url = get_asyncpg_db_url()
    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            """SELECT
                 (SELECT COUNT(*)::int FROM signals WHERE user_id=$1) AS sig_total,
                 (SELECT COUNT(*)::int FROM signals WHERE user_id=$1
                    AND signal_date >= NOW() - INTERVAL '7 days') AS sig_week,
                 (SELECT COUNT(*)::int FROM opportunities WHERE user_id=$1) AS opp_total,
                 (SELECT COUNT(*)::int FROM opportunities WHERE user_id=$1
                    AND created_at >= NOW() - INTERVAL '7 days') AS opp_new,
                 (SELECT COUNT(*)::int FROM actions WHERE user_id=$1) AS act_total,
                 (SELECT COUNT(*)::int FROM actions WHERE user_id=$1
                    AND status='DONE') AS act_done
            """,
            uid
        )
    finally:
        await conn.close()

    return DashboardStats(
        signals_this_week=row['sig_week'] or 0,
        new_opportunities=row['opp_new'] or 0,
        actions_completed=row['act_done'] or 0,
        pipeline_stages=PipelineStages(
            signals=row['sig_total'] or 0,
            opportunities=row['opp_total'] or 0,
            actions=row['act_total'] or 0,
            outreach=0,
        ),
    )


@router.get("/costs", response_model=list[CostEntry])
async def get_agent_costs(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
) -> list[CostEntry]:
    """Return agent cost breakdown by agent_name."""
    settings = get_settings()
    if settings.USE_MOCK_DATA:
        return []

    import asyncpg
    import uuid as _uuid
    from app.db.session import get_asyncpg_db_url
    user_id = current_user["id"]
    uid = _uuid.UUID(user_id)

    conditions = ["user_id = $1"]
    args: list = [uid]
    idx = 2
    if date_from:
        conditions.append(f"created_at >= ${idx}")
        args.append(date_from)
        idx += 1
    if date_to:
        conditions.append(f"created_at <= ${idx}")
        args.append(date_to)
        idx += 1
    where = " AND ".join(conditions)

    db_url = get_asyncpg_db_url()
    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            f"SELECT agent_name, tokens_in, tokens_out, cost_usd FROM agent_runs WHERE {where}",
            *args
        )
    finally:
        await conn.close()

    agg: dict[str, CostEntry] = {}
    for row in rows:
        name = row["agent_name"]
        if name not in agg:
            agg[name] = CostEntry(agent_name=name, calls=0, total_tokens=0, cost_usd=0.0)
        agg[name].calls += 1
        agg[name].total_tokens += (row["tokens_in"] or 0) + (row["tokens_out"] or 0)
        agg[name].cost_usd += row["cost_usd"] or 0.0

    return sorted(agg.values(), key=lambda e: e.cost_usd, reverse=True)
