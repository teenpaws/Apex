"""
Companies API routes — company detail endpoints.

All routes are protected by JWT auth (or mock auth when USE_MOCK_DATA=True).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get a company by ID with its associated signals."""
    settings = get_settings()
    service = CompanyService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    return await service.get_company(company_id)
