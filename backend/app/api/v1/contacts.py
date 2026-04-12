"""
Contacts API routes.

All routes are protected by JWT auth (or mock auth when USE_MOCK_DATA=True).

Endpoints:
  GET  /contacts            — list user's saved contacts (filterable by company)
  POST /contacts/search     — search PDL by company + title keywords
  GET  /contacts/{id}       — contact detail
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.services.contact_service import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


# ── Request / Response schemas ─────────────────────────────────────────────────

class ContactSearchRequest(BaseModel):
    """Request body for POST /contacts/search."""

    company_name: str = Field(..., description="Company to search within")
    title_keywords: list[str] = Field(
        ...,
        min_length=1,
        description="Job title fragments to match (e.g. ['VP Strategy', 'Principal'])",
    )
    limit: int = Field(10, ge=1, le=10, description="Max results (capped at 10)")


class ContactsResponse(BaseModel):
    """Response wrapper for contact lists."""

    contacts: list[dict]
    total: int


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=ContactsResponse)
async def list_contacts(
    company_id: str | None = Query(None, description="Filter by company ID"),
    current_user: dict = Depends(get_current_user),
) -> ContactsResponse:
    """List contacts saved by the authenticated user."""
    settings = get_settings()
    service = ContactService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    result = await service.list_contacts(company_id=company_id)
    return ContactsResponse(**result)


@router.post("/search", response_model=ContactsResponse)
async def search_contacts(
    body: ContactSearchRequest,
    current_user: dict = Depends(get_current_user),
) -> ContactsResponse:
    """
    Search People Data Labs for contacts at a company matching title keywords.

    Results are ranked by seniority (VP > Director > Manager > ...).
    """
    settings = get_settings()
    service = ContactService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    result = await service.search_contacts(
        company_name=body.company_name,
        title_keywords=body.title_keywords,
        limit=body.limit,
    )
    return ContactsResponse(**result)


@router.get("/{contact_id}")
async def get_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get a single contact by ID."""
    settings = get_settings()
    service = ContactService(user_id=current_user["id"], use_mock=settings.USE_MOCK_DATA)
    return await service.get_contact(contact_id)
