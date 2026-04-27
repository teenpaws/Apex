"""Agents API routes — run status polling and run history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/agents", tags=["agents"])


class RunStatus(BaseModel):
    run_id: str
    status: str                        # QUEUED | RUNNING | SUCCESS | FAILED
    stage: str = "QUEUED"              # INGEST | CLASSIFY | PREDICT | FIT_SCORE | ACTIONS | DONE
    completed: int = 0
    total: int = 0
    eta_seconds: int | None = None
    progress: int = 0                  # 0-100 overall percent
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


class PipelineRunResponse(BaseModel):
    run_id: str
    status: str
    message: str


@router.get("/run-status/{run_id}", response_model=RunStatus)
async def get_run_status(
    run_id: str,
    current_user: dict = Depends(get_current_user),
) -> RunStatus:
    """Poll the status of a background agent run."""
    settings = get_settings()
    if settings.USE_MOCK_DATA:
        return RunStatus(run_id=run_id, status="SUCCESS", stage="DONE", completed=100, total=100, progress=100)

    # Try Redis first for real-time stage data
    try:
        import redis as redis_lib  # noqa: PLC0415
        import json as _json  # noqa: PLC0415
        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        redis_data = r.get(f"pipeline:{run_id}:progress")
        if redis_data:
            data = _json.loads(redis_data)
            return RunStatus(run_id=run_id, **data)
    except Exception:  # noqa: BLE001
        pass

    from app.db.session import get_db_client  # noqa: PLC0415
    db = get_db_client()
    user_id = current_user["id"]
    res = db.table("agent_runs").select("*").eq("id", run_id).eq("user_id", user_id).maybe_single().execute()
    if not res.data:
        # Run not in DB yet (worker still starting) — return in-progress status
        return RunStatus(
            run_id=run_id,
            status="RUNNING",
            stage="INGEST",
            progress=5,
        )
    row = res.data
    is_done = row["status"] in ("SUCCESS", "FAILED")
    return RunStatus(
        run_id=run_id,
        status=row["status"],
        stage="DONE" if is_done else "RUNNING",
        progress=100 if is_done else 50,
        result_id=row.get("id"),
        error_message=row.get("error_message"),
    )


@router.post("/pipeline/run", response_model=PipelineRunResponse)
async def trigger_pipeline_run(
    current_user: dict = Depends(get_current_user),
) -> PipelineRunResponse:
    """Trigger a full pipeline run: ingest -> classify -> predict -> fit-score -> actions."""
    import uuid  # noqa: PLC0415
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        return PipelineRunResponse(
            run_id=str(uuid.uuid4()),
            status="queued",
            message="Mock pipeline run started (USE_MOCK_DATA=true)",
        )

    # Full orchestrator: ingest -> classify -> predict (-> fit -> actions, chained)
    from app.workers.run_pipeline import run_full_pipeline  # noqa: PLC0415
    task = run_full_pipeline.delay(user_id=current_user["id"])
    run_id = str(task.id)
    return PipelineRunResponse(
        run_id=run_id,
        status="queued",
        message="Full pipeline queued — ingest, classify, predict, fit-score, actions",
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
