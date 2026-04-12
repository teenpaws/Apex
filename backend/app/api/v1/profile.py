"""
Profile API — GET/PUT routes for the user's career profile.

All routes require a valid Bearer token (or mock-user in USE_MOCK_DATA mode).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from pydantic import BaseModel

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


# ── Request schema ────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    current_role: str | None = None
    target_roles: list[str] | None = None
    industries: list[str] | None = None
    aspirations_text: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=dict,
    summary="Get career profile",
    description="Returns the career profile for the authenticated user.",
)
async def get_profile(
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = ProfileService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    return await service.get_profile()


@router.put(
    "",
    response_model=dict,
    summary="Update career profile",
    description="Partially update the career profile for the authenticated user.",
)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = ProfileService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    return await service.update_profile(body.model_dump())
