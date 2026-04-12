"""
Opportunities API — GET/POST routes for predicted opportunities.

All routes require a valid Bearer token (or mock-user in USE_MOCK_DATA mode).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from pydantic import BaseModel

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


# ── Response schemas ──────────────────────────────────────────────────────────

class PaginatedOpportunitiesResponse(BaseModel):
    opportunities: list[dict]
    total: int
    page: int
    page_size: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedOpportunitiesResponse,
    summary="List predicted opportunities",
    description=(
        "Returns a paginated list of predicted opportunities for the authenticated user. "
        "Supports optional filtering by confidence band, status, and company."
    ),
)
async def list_opportunities(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    confidence: str | None = Query(None, description="Filter by confidence: HIGH, MEDIUM, SPECULATIVE"),
    status: str | None = Query(None, description="Filter by status: PREDICTED, APPROACHED, INTERVIEWING, CLOSED"),
    company_id: str | None = Query(None, description="Filter by company UUID"),
    current_user: dict = Depends(get_current_user),
) -> PaginatedOpportunitiesResponse:
    settings = get_settings()
    service = OpportunityService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    result = await service.list_opportunities(
        page=page,
        page_size=page_size,
        confidence=confidence,
        status=status,
        company_id=company_id,
    )
    return PaginatedOpportunitiesResponse(**result)


@router.get(
    "/{opportunity_id}",
    response_model=dict,
    summary="Get opportunity detail",
    description="Returns a single opportunity by ID. 404 if not found or not owned by the user.",
)
async def get_opportunity(
    opportunity_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = OpportunityService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    return await service.get_opportunity(opportunity_id)


@router.post(
    "/{opportunity_id}/refresh",
    summary="Re-score opportunity",
    description=(
        "Enqueues an async re-scoring job for the given opportunity. "
        "Returns a run_id to poll via GET /agents/run-status/{run_id}."
    ),
)
async def refresh_opportunity(
    opportunity_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = OpportunityService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    return await service.refresh_opportunity(opportunity_id)
