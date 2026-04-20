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
