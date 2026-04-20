"""
Signals API routes — market intelligence signal endpoints.

All routes are protected by JWT auth (or mock auth when USE_MOCK_DATA=True).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.services.signal_service import SignalService
from pydantic import BaseModel

router = APIRouter(prefix="/signals", tags=["signals"])


class PaginatedSignalsResponse(BaseModel):
    """Paginated list of signals.

    Field names match the frontend ``PaginatedResponse<T>`` TypeScript type:
    ``data`` (array), ``total``, ``page``, ``per_page``.
    """
    data: list[dict]
    total: int
    page: int
    per_page: int


class IngestRequest(BaseModel):
    """Request body for triggering signal ingestion."""
    source: str | None = None


@router.get("", response_model=PaginatedSignalsResponse)
async def list_signals(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    page_size: int | None = Query(None, include_in_schema=False),  # legacy alias
    signal_type: str | None = Query(None, description="Filter by signal type (e.g. FUNDING)"),
    company_id: str | None = Query(None, description="Filter by company ID"),
    date_from: str | None = Query(None, description="Filter signals on or after this date (ISO 8601)"),
    date_to: str | None = Query(None, description="Filter signals on or before this date (ISO 8601)"),
    current_user: dict = Depends(get_current_user),
) -> PaginatedSignalsResponse:
    """List signals for the authenticated user with optional filters."""
    settings = get_settings()
    effective_page_size = page_size or per_page
    service = SignalService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    result = await service.list_signals(
        page=page,
        page_size=effective_page_size,
        signal_type=signal_type,
        company_id=company_id,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedSignalsResponse(**result)


@router.get("/{signal_id}", response_model=dict)
async def get_signal(
    signal_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get a single signal by ID."""
    settings = get_settings()
    service = SignalService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    return await service.get_signal(signal_id)


@router.post("/ingest")
async def trigger_ingest(
    body: IngestRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Trigger signal ingestion. Returns a run_id to poll for status."""
    settings = get_settings()
    service = SignalService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    return await service.trigger_ingest(source=body.source)


@router.post("/classify")
async def trigger_classify(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Batch-classify all unprocessed signals for the current user.

    Dispatches classify_signal Celery tasks for every signal where
    processed_at IS NULL. Returns count of tasks queued.
    """
    import asyncpg  # noqa: PLC0415
    import uuid  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415
    from app.workers.classify_signals import batch_classify_signals  # noqa: PLC0415

    settings = get_settings()
    db_url = get_asyncpg_db_url()
    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            "SELECT id FROM signals WHERE user_id = $1 AND processed_at IS NULL",
            uuid.UUID(current_user["id"]),
        )
        signal_ids = [str(r["id"]) for r in rows]
    finally:
        await conn.close()

    if not signal_ids:
        return {"queued": 0, "message": "No unprocessed signals found"}

    batch_classify_signals.delay(signal_ids)
    return {
        "queued": len(signal_ids),
        "message": f"Queued {len(signal_ids)} signals for classification",
    }
