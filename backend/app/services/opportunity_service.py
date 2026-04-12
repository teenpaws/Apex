"""
Opportunity service — business logic for predicted opportunities.

In mock mode (USE_MOCK_DATA=True) all operations are served from
backend/app/api/mock_responses/opportunities.json.

Live mode stubs raise NotImplementedError until the Supabase DB layer
is wired in a later sprint.
"""

from __future__ import annotations

import copy
from uuid import uuid4

from app.core.errors import ApexHTTPException
from app.services._mock_loader import load_mock


class OpportunityService:
    """Service layer for opportunity operations, scoped to a single user."""

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_opportunities(
        self,
        page: int = 1,
        page_size: int = 20,
        confidence: str | None = None,
        status: str | None = None,
        company_id: str | None = None,
    ) -> dict:
        """
        Return a paginated list of opportunities for this user.

        Filters (confidence, status, company_id) are applied in Python in
        mock mode. Live mode is not yet implemented.
        """
        if self.use_mock:
            return self._mock_list(
                page=page,
                page_size=page_size,
                confidence=confidence,
                status=status,
                company_id=company_id,
            )
        raise NotImplementedError("Live DB not yet wired")

    def _mock_list(
        self,
        page: int,
        page_size: int,
        confidence: str | None,
        status: str | None,
        company_id: str | None,
    ) -> dict:
        data = load_mock("opportunities.json")
        items: list[dict] = data["opportunities"]

        # Filter by user_id to honour the user-scoping invariant even in mock.
        items = [o for o in items if o.get("user_id") == self.user_id]

        if confidence is not None:
            items = [o for o in items if o.get("confidence") == confidence.upper()]

        if status is not None:
            items = [o for o in items if o.get("status") == status.upper()]

        if company_id is not None:
            items = [o for o in items if o.get("company_id") == company_id]

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        return {
            "opportunities": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Get single ────────────────────────────────────────────────────────────

    async def get_opportunity(self, opportunity_id: str) -> dict:
        """
        Return a single opportunity by ID.

        Raises 404 if not found (or not owned by this user).
        """
        if self.use_mock:
            return self._mock_get(opportunity_id)
        raise NotImplementedError("Live DB not yet wired")

    def _mock_get(self, opportunity_id: str) -> dict:
        data = load_mock("opportunities.json")
        for opp in data["opportunities"]:
            if opp["id"] == opportunity_id and opp.get("user_id") == self.user_id:
                return opp
        raise ApexHTTPException(
            status_code=404,
            error="Opportunity not found",
            code="OPPORTUNITY_NOT_FOUND",
        )

    # ── Refresh ───────────────────────────────────────────────────────────────

    async def refresh_opportunity(self, opportunity_id: str) -> dict:
        """
        Enqueue an opportunity re-scoring job.

        Returns a run_id that the caller can poll via GET /agents/run-status/{run_id}.
        Works the same in both mock and live mode — the actual processing is async.
        """
        return {
            "run_id": str(uuid4()),
            "status": "queued",
            "message": "Opportunity re-scoring queued",
        }
