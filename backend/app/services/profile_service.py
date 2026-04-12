"""
Profile service — business logic for career profiles.

In mock mode (USE_MOCK_DATA=True) all operations are served from
backend/app/api/mock_responses/profile.json.

Live mode stubs raise NotImplementedError until the Supabase DB layer
is wired in a later sprint.
"""

from __future__ import annotations

import copy

from app.services._mock_loader import load_mock


class ProfileService:
    """Service layer for career profile operations, scoped to a single user."""

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    # ── Get ───────────────────────────────────────────────────────────────────

    async def get_profile(self) -> dict:
        """Return the career profile for this user."""
        if self.use_mock:
            return load_mock("profile.json")
        raise NotImplementedError("Live DB not yet wired")

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_profile(self, updates: dict) -> dict:
        """
        Apply a partial update to the career profile and return the merged result.

        Mock mode: merges in-memory without mutating the JSON file.
        """
        if self.use_mock:
            return self._mock_update(updates)
        raise NotImplementedError("Live DB not yet wired")

    def _mock_update(self, updates: dict) -> dict:
        profile = copy.deepcopy(load_mock("profile.json"))
        for key, value in updates.items():
            if value is not None:
                profile[key] = value
        return profile
