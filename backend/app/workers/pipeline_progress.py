"""Pipeline progress reporting — writes stage updates to Redis for FE polling."""
from __future__ import annotations
import json
import logging

try:
    import redis  # noqa: F401 — imported at module level so tests can patch it
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
_TTL_SECONDS = 86_400

STAGE_WEIGHTS = {
    "INGEST": 5, "CLASSIFY": 40, "PREDICT": 30,
    "FIT_SCORE": 15, "ACTIONS": 10, "DONE": 100,
}
STAGE_ORDER = ["INGEST", "CLASSIFY", "PREDICT", "FIT_SCORE", "ACTIONS", "DONE"]


def report_stage(
    run_id: str,
    stage: str,
    status: str,
    completed: int,
    total: int,
    eta_seconds: int | None = None,
    redis_url: str = "redis://localhost:6379/0",
) -> None:
    """Write pipeline stage progress to Redis. Silent on failure — never crashes workers."""
    stage_progress = (completed / total * 100) if total > 0 else 0
    stage_weight = STAGE_WEIGHTS.get(stage, 0)
    prior_weight = sum(
        w for s, w in STAGE_WEIGHTS.items()
        if STAGE_ORDER.index(s) < STAGE_ORDER.index(stage)
    ) if stage in STAGE_ORDER else 0
    overall_progress = min(int(prior_weight + (stage_progress / 100) * stage_weight), 99)
    if stage == "DONE":
        overall_progress = 100

    data = {
        "status": "SUCCESS" if stage == "DONE" else status,
        "stage": stage,
        "completed": completed,
        "total": total,
        "progress": overall_progress,
        "eta_seconds": eta_seconds,
    }
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        r.set(f"pipeline:{run_id}:progress", json.dumps(data), ex=_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write pipeline progress to Redis: %s", exc)
