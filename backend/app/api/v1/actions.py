"""
Actions API — GET/PUT routes for the user's task queue.

All routes require a valid Bearer token (or mock-user in USE_MOCK_DATA mode).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from pydantic import BaseModel

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.services.action_service import ActionService

router = APIRouter(prefix="/actions", tags=["actions"])


# ── Request / response schemas ────────────────────────────────────────────────

class PaginatedActionsResponse(BaseModel):
    """Paginated list of actions.

    Field names match the frontend ``PaginatedResponse<T>`` TypeScript type:
    ``data`` (array), ``total``, ``page``, ``per_page``.
    """
    data: list[dict]
    total: int
    page: int
    per_page: int


class ActionUpdateRequest(BaseModel):
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedActionsResponse,
    summary="List actions",
    description=(
        "Returns a paginated task queue for the authenticated user. "
        "Supports optional filtering by status and priority."
    ),
)
async def list_actions(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    page_size: int | None = Query(None, include_in_schema=False),  # legacy alias
    status: str | None = Query(None, description="Filter by status: TODO, IN_PROGRESS, DONE, SNOOZED"),
    priority: str | None = Query(None, description="Filter by priority: HIGH, MEDIUM, LOW"),
    current_user: dict = Depends(get_current_user),
) -> PaginatedActionsResponse:
    settings = get_settings()
    effective_page_size = page_size or per_page
    service = ActionService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    result = await service.list_actions(
        page=page,
        page_size=effective_page_size,
        status=status,
        priority=priority,
    )
    return PaginatedActionsResponse(**result)


@router.put(
    "/{action_id}",
    response_model=dict,
    summary="Update action",
    description="Partially update an action's status, priority, or due date. 404 if not found.",
)
async def update_action(
    action_id: str,
    body: ActionUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = ActionService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    return await service.update_action(action_id, body.model_dump())


@router.post(
    "/{action_id}/draft-email",
    summary="Generate email draft",
    description=(
        "Enqueues an async email-draft generation job for the given action. "
        "Returns a run_id to poll via GET /agents/run-status/{run_id}."
    ),
)
async def draft_email_for_action(
    action_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = ActionService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    return await service.draft_email_for_action(action_id)
