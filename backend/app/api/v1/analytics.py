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

    from app.db.session import get_db_client
    from datetime import datetime, timedelta, timezone
    db = get_db_client()
    user_id = current_user["id"]
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    sig_res = db.table("signals").select("id", count="exact").eq("user_id", user_id).gte("signal_date", week_ago[:10]).execute()
    opp_res = db.table("opportunities").select("id", count="exact").eq("user_id", user_id).gte("created_at", week_ago).execute()
    act_done_res = db.table("actions").select("id", count="exact").eq("user_id", user_id).eq("status", "DONE").execute()
    sig_total = db.table("signals").select("id", count="exact").eq("user_id", user_id).execute()
    opp_total = db.table("opportunities").select("id", count="exact").eq("user_id", user_id).execute()
    act_total = db.table("actions").select("id", count="exact").eq("user_id", user_id).execute()
    out_total = db.table("outreach_emails").select("id", count="exact").eq("user_id", user_id).execute()

    return DashboardStats(
        signals_this_week=sig_res.count or 0,
        new_opportunities=opp_res.count or 0,
        actions_completed=act_done_res.count or 0,
        pipeline_stages=PipelineStages(
            signals=sig_total.count or 0,
            opportunities=opp_total.count or 0,
            actions=act_total.count or 0,
            outreach=out_total.count or 0,
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

    from app.db.session import get_db_client
    db = get_db_client()
    user_id = current_user["id"]
    query = db.table("agent_runs").select("*").eq("user_id", user_id)
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", date_to)
    rows = query.execute().data or []

    agg: dict[str, CostEntry] = {}
    for row in rows:
        name = row["agent_name"]
        if name not in agg:
            agg[name] = CostEntry(agent_name=name, calls=0, total_tokens=0, cost_usd=0.0)
        agg[name].calls += 1
        agg[name].total_tokens += (row.get("tokens_in") or 0) + (row.get("tokens_out") or 0)
        agg[name].cost_usd += row.get("cost_usd") or 0.0

    return sorted(agg.values(), key=lambda e: e.cost_usd, reverse=True)
