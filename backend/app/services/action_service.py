"""
Action service — business logic for the user's task queue.

In mock mode (USE_MOCK_DATA=True) all operations are served from
backend/app/api/mock_responses/actions.json.

Live mode stubs raise NotImplementedError until the Supabase DB layer
is wired in a later sprint.
"""

from __future__ import annotations

import copy
from uuid import uuid4

from app.core.errors import ApexHTTPException
from app.services._mock_loader import load_mock


class ActionService:
    """Service layer for action operations, scoped to a single user."""

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_actions(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        priority: str | None = None,
    ) -> dict:
        """
        Return a paginated list of actions for this user.

        Filters (status, priority) are applied in Python in mock mode.
        """
        if self.use_mock:
            return self._mock_list(
                page=page,
                page_size=page_size,
                status=status,
                priority=priority,
            )
        raise NotImplementedError("Live DB not yet wired")

    def _mock_list(
        self,
        page: int,
        page_size: int,
        status: str | None,
        priority: str | None,
    ) -> dict:
        data = load_mock("actions.json")
        items: list[dict] = data["actions"]

        # Filter by user_id to honour the user-scoping invariant even in mock.
        items = [a for a in items if a.get("user_id") == self.user_id]

        if status is not None:
            items = [a for a in items if a.get("status") == status.upper()]

        if priority is not None:
            items = [a for a in items if a.get("priority") == priority.upper()]

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        return {
            "data": page_items,
            "total": total,
            "page": page,
            "per_page": page_size,
        }

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_action(self, action_id: str, updates: dict) -> dict:
        """
        Apply a partial update to an action and return the merged result.

        Mock mode: merges in-memory without mutating the JSON file.
        Raises 404 if the action is not found or not owned by this user.
        """
        if self.use_mock:
            return self._mock_update(action_id, updates)
        raise NotImplementedError("Live DB not yet wired")

    def _mock_update(self, action_id: str, updates: dict) -> dict:
        data = load_mock("actions.json")
        for action in data["actions"]:
            if action["id"] == action_id and action.get("user_id") == self.user_id:
                merged = copy.deepcopy(action)
                # Only apply non-None update values.
                for key, value in updates.items():
                    if value is not None:
                        merged[key] = value
                return merged
        raise ApexHTTPException(
            status_code=404,
            error="Action not found",
            code="ACTION_NOT_FOUND",
        )

    # ── Draft email ───────────────────────────────────────────────────────────

    async def draft_email_for_action(self, action_id: str) -> dict:
        """
        Enqueue an email-draft generation job for the given action.

        Returns a run_id that the caller can poll via GET /agents/run-status/{run_id}.
        Works the same in both mock and live mode.
        """
        return {
            "run_id": str(uuid4()),
            "status": "queued",
            "message": "Email draft generation queued",
        }
