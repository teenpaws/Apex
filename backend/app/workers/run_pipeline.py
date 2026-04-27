"""
Full pipeline orchestrator — runs the entire chain in one Celery task:

    ingest -> classify -> predict (chains to fit_score -> actions automatically)

The task is intentionally long-running (5-15 min for 15 companies). It runs
synchronously inside one Celery worker thread so progress is observable in the
log and any failure is contained to a single task ID.

Triggered by: POST /api/v1/agents/pipeline/run

Why one task instead of Celery chord/chain primitives?
  - Chord requires a results backend, which we don't configure in dev.
  - Linear orchestration is far easier to reason about for a single-user MVP.
  - The user-facing /agents/run-status/{run_id} polls the parent task ID.
"""
from __future__ import annotations

import asyncio
import json
import logging

from app.core.celery_app import celery_app
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _write_progress(run_id: str, **fields) -> None:
    """Write progress snapshot to Redis so /agents/run-status/{id} can read it.

    Key format: pipeline:{run_id}:progress, TTL 1 hour.
    Fields match the RunStatus pydantic shape (status, stage, completed, total,
    progress, eta_seconds, result_id, error_message).
    """
    try:
        import redis as redis_lib
        settings = get_settings()
        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        r.setex(f"pipeline:{run_id}:progress", 3600, json.dumps(fields))
    except Exception as exc:  # noqa: BLE001
        logger.debug("progress write skipped: %s", exc)


@celery_app.task(
    name="app.workers.run_pipeline.run_full_pipeline",
    bind=True,
    queue="default",
)
def run_full_pipeline(self, user_id: str) -> dict:
    """Ingest -> classify -> predict for one user. Returns aggregate counts."""
    from app.workers.ingest_signals import ingest_all_sources
    from app.workers.classify_signals import batch_classify_signals_upgrade
    from app.workers.predict_opportunities import predict_for_company

    run_id = self.request.id
    logger.info("run_full_pipeline: starting run_id=%s user_id=%s", run_id, user_id)
    _write_progress(run_id, status="RUNNING", stage="INGEST", progress=5)

    # ── Stage 1: Ingest ───────────────────────────────────────────────────────
    ingest_result = ingest_all_sources.run(user_id=user_id)
    logger.info("run_full_pipeline: ingest done — %s", ingest_result)
    _write_progress(run_id, status="RUNNING", stage="CLASSIFY", progress=25)

    # ── Stage 2: Classify all unprocessed signals ─────────────────────────────
    signal_ids = asyncio.run(_fetch_unprocessed_signal_ids(user_id))
    logger.info("run_full_pipeline: %d unprocessed signals to classify", len(signal_ids))

    classify_total = {"total": 0, "pre_filtered": 0, "classified": 0, "failed": 0}
    if signal_ids:
        BATCH = 50
        total_batches = (len(signal_ids) + BATCH - 1) // BATCH
        for i in range(0, len(signal_ids), BATCH):
            batch = signal_ids[i : i + BATCH]
            result = batch_classify_signals_upgrade.run(signal_ids=batch)
            for k in classify_total:
                classify_total[k] += result.get(k, 0)
            # Classify spans 25% -> 65% of overall progress
            pct = 25 + int(40 * ((i // BATCH) + 1) / total_batches)
            _write_progress(
                run_id, status="RUNNING", stage="CLASSIFY",
                completed=classify_total["total"], total=len(signal_ids), progress=pct,
            )
        logger.info("run_full_pipeline: classify done — %s", classify_total)

    _write_progress(run_id, status="RUNNING", stage="PREDICT", progress=70)

    # ── Stage 3: Predict opportunities ────────────────────────────────────────
    # predict_for_company chains internally into score_fit and generate_actions.
    company_ids = asyncio.run(_fetch_companies_with_relevant_signals(user_id))
    logger.info(
        "run_full_pipeline: %d companies have relevance>=0.4 signals — queuing predict",
        len(company_ids),
    )
    for cid in company_ids:
        predict_for_company.apply_async(args=[user_id, cid], queue="default")

    _write_progress(
        run_id, status="SUCCESS", stage="DONE", progress=100,
        completed=classify_total["total"], total=classify_total["total"],
    )

    return {
        "ingest": ingest_result,
        "classify": classify_total,
        "predict_queued": len(company_ids),
    }


# ── DB helpers ────────────────────────────────────────────────────────────────


async def _fetch_unprocessed_signal_ids(user_id: str) -> list[str]:
    import asyncpg
    import uuid as _uuid
    from app.db.session import get_asyncpg_db_url

    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        rows = await conn.fetch(
            """SELECT id FROM signals
               WHERE user_id = $1 AND processed_at IS NULL AND is_duplicate = false""",
            _uuid.UUID(user_id),
        )
        return [str(r["id"]) for r in rows]
    finally:
        await conn.close()


async def _fetch_companies_with_relevant_signals(user_id: str) -> list[str]:
    import asyncpg
    import uuid as _uuid
    from app.db.session import get_asyncpg_db_url

    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        rows = await conn.fetch(
            """SELECT DISTINCT company_id FROM signals
               WHERE user_id = $1
                 AND processed_at IS NOT NULL
                 AND relevance_score >= 0.4
                 AND is_duplicate = false
                 AND company_id IS NOT NULL""",
            _uuid.UUID(user_id),
        )
        return [str(r["company_id"]) for r in rows]
    finally:
        await conn.close()
