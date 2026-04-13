"""Agents API routes — run status polling and run history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/agents", tags=["agents"])


class RunStatus(BaseModel):
    run_id: str
    status: str
    progress: int = 0
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
    """Poll the status of a background agent run."""
    settings = get_settings()
    if settings.USE_MOCK_DATA:
        return RunStatus(run_id=run_id, status="SUCCESS", progress=100)

    from app.db.session import get_db_client
    db = get_db_client()
    user_id = current_user["id"]
    res = db.table("agent_runs").select("*").eq("id", run_id).eq("user_id", user_id).maybe_single().execute()
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

    from app.db.session import get_db_client
    db = get_db_client()
    user_id = current_user["id"]
    rows = db.table("agent_runs").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(100).execute().data or []
    return [AgentRunRead(**r) for r in rows]
