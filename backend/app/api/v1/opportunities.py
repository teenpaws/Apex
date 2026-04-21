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
    """Paginated list of opportunities.

    Field names match the frontend ``PaginatedResponse<T>`` TypeScript type:
    ``data`` (array), ``total``, ``page``, ``per_page``.
    """
    data: list[dict]
    total: int
    page: int
    per_page: int


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
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    page_size: int | None = Query(None, include_in_schema=False),  # legacy alias
    confidence: str | None = Query(None, description="Filter by confidence: HIGH, MEDIUM, SPECULATIVE"),
    status: str | None = Query(None, description="Filter by status: PREDICTED, APPROACHED, INTERVIEWING, CLOSED"),
    company_id: str | None = Query(None, description="Filter by company UUID"),
    current_user: dict = Depends(get_current_user),
) -> PaginatedOpportunitiesResponse:
    settings = get_settings()
    effective_page_size = page_size or per_page
    service = OpportunityService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    result = await service.list_opportunities(
        page=page,
        page_size=effective_page_size,
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
    "/predict",
    summary="Trigger opportunity prediction",
    description=(
        "Finds all companies that have classified signals with relevance >= 0.4 "
        "and queues OpportunityPredictorAgent for each. Chains automatically into "
        "CareerFitScorer → ActionGenerator. Returns count of companies queued."
    ),
)
async def trigger_predict(
    current_user: dict = Depends(get_current_user),
) -> dict:
    import asyncpg  # noqa: PLC0415
    import uuid  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415
    from app.workers.predict_opportunities import predict_for_company  # noqa: PLC0415

    db_url = get_asyncpg_db_url()
    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT company_id
            FROM signals
            WHERE user_id = $1
              AND processed_at IS NOT NULL
              AND relevance_score >= 0.4
              AND is_duplicate = false
              AND company_id IS NOT NULL
            """,
            uuid.UUID(current_user["id"]),
        )
        company_ids = [str(r["company_id"]) for r in rows]
    finally:
        await conn.close()

    if not company_ids:
        return {
            "queued": 0,
            "message": "No companies with relevant classified signals — run signal classification first",
        }

    for company_id in company_ids:
        predict_for_company.apply_async(
            args=[current_user["id"], company_id],
            queue="default",
        )

    return {
        "queued": len(company_ids),
        "company_ids": company_ids,
        "message": f"Queued opportunity prediction for {len(company_ids)} companies. Pipeline: predict → fit score → actions.",
    }


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
