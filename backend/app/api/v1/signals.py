"""
Signals API routes — market intelligence signal endpoints.

All routes are protected by JWT auth (or mock auth when USE_MOCK_DATA=True).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.models.signal import SignalRead
from app.services.signal_service import SignalService
from pydantic import BaseModel

router = APIRouter(prefix="/signals", tags=["signals"])


class PaginatedSignalsResponse(BaseModel):
    """Paginated list of signals.

    Field names match the frontend ``PaginatedResponse<T>`` TypeScript type:
    ``data`` (array), ``total``, ``page``, ``per_page``.
    """
    data: list[SignalRead]
    total: int
    page: int
    per_page: int


class IngestRequest(BaseModel):
    """Request body for triggering signal ingestion."""
    source: str | None = None


@router.get("", response_model=PaginatedSignalsResponse)
async def list_signals(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    signal_type: str | None = Query(None, description="Filter by signal type (e.g. FUNDING)"),
    company_id: str | None = Query(None, description="Filter by company ID"),
    date_from: str | None = Query(None, description="Filter signals on or after this date (ISO 8601)"),
    date_to: str | None = Query(None, description="Filter signals on or before this date (ISO 8601)"),
    current_user: dict = Depends(get_current_user),
) -> PaginatedSignalsResponse:
    """List signals for the authenticated user with optional filters."""
    settings = get_settings()
    service = SignalService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    result = await service.list_signals(
        page=page,
        page_size=page_size,
        signal_type=signal_type,
        company_id=company_id,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedSignalsResponse(**result)


@router.get("/{signal_id}", response_model=SignalRead)
async def get_signal(
    signal_id: str,
    current_user: dict = Depends(get_current_user),
) -> SignalRead:
    """Get a single signal by ID."""
    settings = get_settings()
    service = SignalService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    result = await service.get_signal(signal_id)
    return SignalRead.model_validate(result)


@router.post("/ingest")
async def trigger_ingest(
    body: IngestRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Trigger signal ingestion. Returns a run_id to poll for status."""
    settings = get_settings()
    service = SignalService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    return await service.trigger_ingest(source=body.source)
