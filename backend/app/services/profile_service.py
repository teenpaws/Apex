"""
Profile service — business logic for career profiles.

In mock mode (USE_MOCK_DATA=True) all operations are served from
backend/app/api/mock_responses/profile.json.

Live mode: queries Supabase via asyncpg (pgbouncer-compatible).
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
        if self.use_mock:
            return load_mock("profile.json")
        return await self._live_get()

    async def _live_get(self) -> dict:
        import asyncpg
        import uuid
        from app.db.session import get_asyncpg_db_url

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                '''SELECT id, user_id, "current_role", target_roles, industries,
                          aspirations_text, updated_at
                   FROM career_profiles WHERE user_id = $1''',
                uuid.UUID(self.user_id)
            )
            if not row:
                return {
                    'id': None,
                    'user_id': self.user_id,
                    'current_role': '',
                    'target_roles': [],
                    'industries': [],
                    'aspirations_text': '',
                    'updated_at': None,
                }
            return {
                'id': str(row['id']) if row['id'] else None,
                'user_id': str(row['user_id']),
                'current_role': row['current_role'] or '',
                'target_roles': list(row['target_roles'] or []),
                'industries': list(row['industries'] or []),
                'aspirations_text': row['aspirations_text'] or '',
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            }
        finally:
            await conn.close()

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_profile(self, updates: dict) -> dict:
        if self.use_mock:
            return self._mock_update(updates)
        return await self._live_update(updates)

    async def _live_update(self, updates: dict) -> dict:
        import asyncpg
        import uuid
        from app.db.session import get_asyncpg_db_url

        allowed = {'"current_role"', 'target_roles', 'industries', 'aspirations_text'}
        set_parts = []
        args: list = []
        idx = 1

        # Map from API field name to DB column
        field_map = {
            'current_role': '"current_role"',
            'target_roles': 'target_roles',
            'industries': 'industries',
            'aspirations_text': 'aspirations_text',
        }

        for key, val in updates.items():
            if key in field_map and val is not None:
                set_parts.append(f'{field_map[key]} = ${idx}')
                args.append(val)
                idx += 1

        if not set_parts:
            return await self._live_get()

        set_parts.append(f'updated_at = NOW()')

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            args.append(uuid.UUID(self.user_id))
            await conn.execute(
                f'''UPDATE career_profiles SET {', '.join(set_parts)}
                    WHERE user_id = ${idx}''',
                *args
            )
            return await self._live_get()
        finally:
            await conn.close()

    def _mock_update(self, updates: dict) -> dict:
        profile = copy.deepcopy(load_mock("profile.json"))
        for key, value in updates.items():
            if value is not None:
                profile[key] = value
        return profile

    # ── Pending review ────────────────────────────────────────────────────────

    async def get_pending_review(self) -> dict:
        """Return staged extraction output awaiting user approval."""
        if self.use_mock:
            return self._mock_pending_review()
        return await self._live_pending_review()

    def _mock_pending_review(self) -> dict:
        return {
            "has_pending": True,
            "staged": {
                "years_of_experience": 6,
                "seniority_band": "ASSOCIATE",
                "work_history": [
                    {
                        "company": "BCG",
                        "title": "Senior Consultant",
                        "start_year": 2021,
                        "end_year": 2024,
                        "summary": "Strategy engagements.",
                    }
                ],
                "key_achievements": [
                    {
                        "achievement": "Led $12M cost reduction",
                        "impact": "$12M savings",
                        "context": "BCG",
                    }
                ],
                "inferred_skills": ["strategy", "stakeholder management"],
                "cover_letter_narratives": [],
            },
        }

    async def _live_pending_review(self) -> dict:
        import json
        import uuid
        import asyncpg
        from app.db.session import get_asyncpg_db_url

        conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT extraction_staging_json FROM career_profiles WHERE user_id = $1",
                uuid.UUID(self.user_id),
            )
        finally:
            await conn.close()

        if not row or not row["extraction_staging_json"]:
            return {"has_pending": False, "staged": None}

        staged = (
            json.loads(row["extraction_staging_json"])
            if isinstance(row["extraction_staging_json"], str)
            else row["extraction_staging_json"]
        )
        return {"has_pending": True, "staged": staged}

    # ── Approval ──────────────────────────────────────────────────────────────

    async def approve_extraction(self) -> dict:
        """Apply staged extraction fields to career profile."""
        if self.use_mock:
            return {"approved": True, "profile_source": "RESUME"}
        return await self._live_approve()

    async def _live_approve(self) -> dict:
        import json
        import uuid
        import asyncpg
        from app.db.session import get_asyncpg_db_url

        review = await self._live_pending_review()
        if not review["has_pending"]:
            return {"approved": False, "reason": "no pending extraction"}

        staged = review["staged"]

        conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
        try:
            # Determine profile_source
            existing_row = await conn.fetchrow(
                'SELECT "current_role" FROM career_profiles WHERE user_id = $1',
                uuid.UUID(self.user_id),
            )
            has_manual = bool(existing_row and existing_row["current_role"])
            source = "BOTH" if has_manual else "RESUME"

            await conn.execute(
                """UPDATE career_profiles SET
                     years_of_experience   = $1,
                     seniority_band        = $2,
                     education_json        = $3,
                     work_history_json     = $4,
                     key_achievements_json = $5,
                     profile_source        = $6,
                     last_analyzed_at      = NOW(),
                     extraction_staging_json = NULL
                   WHERE user_id = $7""",
                staged.get("years_of_experience"),
                staged.get("seniority_band"),
                json.dumps(staged.get("education", [])),
                json.dumps(staged.get("work_history", [])),
                json.dumps(staged.get("key_achievements", [])),
                source,
                uuid.UUID(self.user_id),
            )
        finally:
            await conn.close()

        return {"approved": True, "profile_source": source}
