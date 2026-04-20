"""
Action service — business logic for the user's task queue.

In mock mode (USE_MOCK_DATA=True) all operations are served from
backend/app/api/mock_responses/actions.json.

Live mode: queries Supabase via asyncpg (pgbouncer-compatible).
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
        if self.use_mock:
            return self._mock_list(
                page=page,
                page_size=page_size,
                status=status,
                priority=priority,
            )
        return await self._live_list(
            page=page,
            page_size=page_size,
            status=status,
            priority=priority,
        )

    async def _live_list(
        self,
        page: int,
        page_size: int,
        status: str | None,
        priority: str | None,
    ) -> dict:
        import asyncpg
        import uuid
        from app.db.session import get_asyncpg_db_url

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            conditions = ['a.user_id = $1']
            args: list = [uuid.UUID(self.user_id)]
            idx = 2

            # status can be comma-separated (e.g. "TODO,IN_PROGRESS")
            if status:
                statuses = [s.strip().upper() for s in status.split(',')]
                placeholders = ','.join(f'${i}' for i in range(idx, idx + len(statuses)))
                conditions.append(f'a.status IN ({placeholders})')
                args.extend(statuses)
                idx += len(statuses)
            if priority:
                conditions.append(f'a.priority = ${idx}')
                args.append(priority.upper())
                idx += 1

            where = ' AND '.join(conditions)

            count_row = await conn.fetchrow(
                f'SELECT COUNT(*) as cnt FROM actions a WHERE {where}',
                *args
            )
            total = count_row['cnt']

            offset = (page - 1) * page_size
            rows = await conn.fetch(
                f'''SELECT a.id, a.user_id, a.opportunity_id, a.company_id,
                           a.title, a.description, a.type, a.priority,
                           a.status, a.due_date, a.source_signal_id,
                           a.ai_draft_json, a.created_at,
                           c.name as company_name
                    FROM actions a
                    LEFT JOIN companies c ON c.id = a.company_id
                    WHERE {where}
                    ORDER BY
                      CASE a.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                      a.due_date ASC NULLS LAST,
                      a.created_at DESC
                    LIMIT ${idx} OFFSET ${idx+1}''',
                *args, page_size, offset
            )

            items = []
            for r in rows:
                items.append({
                    'id': str(r['id']),
                    'user_id': str(r['user_id']),
                    'opportunity_id': str(r['opportunity_id']) if r['opportunity_id'] else None,
                    'company_id': str(r['company_id']) if r['company_id'] else None,
                    'title': r['title'],
                    'description': r['description'] or '',
                    'type': r['type'],
                    'priority': r['priority'],
                    'status': r['status'],
                    'due_date': r['due_date'].isoformat() if r['due_date'] else None,
                    'source_signal_id': str(r['source_signal_id']) if r['source_signal_id'] else None,
                    'ai_draft_json': r['ai_draft_json'] or {},
                    'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                    # UI aliases
                    'company': r['company_name'],
                    'dueDate': r['due_date'].strftime('%d %b') if r['due_date'] else None,
                    'sourceSignalId': str(r['source_signal_id']) if r['source_signal_id'] else None,
                })

            return {'data': items, 'total': total, 'page': page, 'per_page': page_size}
        finally:
            await conn.close()

    def _mock_list(
        self,
        page: int,
        page_size: int,
        status: str | None,
        priority: str | None,
    ) -> dict:
        data = load_mock("actions.json")
        items: list[dict] = data["actions"]

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
        if self.use_mock:
            return self._mock_update(action_id, updates)
        return await self._live_update(action_id, updates)

    async def _live_update(self, action_id: str, updates: dict) -> dict:
        import asyncpg
        import uuid
        from app.db.session import get_asyncpg_db_url

        allowed = {'status', 'priority', 'due_date', 'title', 'description'}
        set_parts = []
        args: list = []
        idx = 1
        for key, val in updates.items():
            if key in allowed and val is not None:
                set_parts.append(f'{key} = ${idx}')
                args.append(val)
                idx += 1

        if not set_parts:
            raise ApexHTTPException(400, "No valid fields to update", code="NO_UPDATES")

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            args.extend([uuid.UUID(action_id), uuid.UUID(self.user_id)])
            row = await conn.fetchrow(
                f'''UPDATE actions SET {', '.join(set_parts)}
                    WHERE id = ${idx} AND user_id = ${idx+1}
                    RETURNING id, user_id, opportunity_id, company_id,
                              title, description, type, priority, status,
                              due_date, source_signal_id, ai_draft_json, created_at''',
                *args
            )
            if not row:
                raise ApexHTTPException(404, "Action not found", code="ACTION_NOT_FOUND")
            return {
                'id': str(row['id']),
                'user_id': str(row['user_id']),
                'opportunity_id': str(row['opportunity_id']) if row['opportunity_id'] else None,
                'company_id': str(row['company_id']) if row['company_id'] else None,
                'title': row['title'],
                'description': row['description'] or '',
                'type': row['type'],
                'priority': row['priority'],
                'status': row['status'],
                'due_date': row['due_date'].isoformat() if row['due_date'] else None,
                'source_signal_id': str(row['source_signal_id']) if row['source_signal_id'] else None,
                'ai_draft_json': row['ai_draft_json'] or {},
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            }
        finally:
            await conn.close()

    def _mock_update(self, action_id: str, updates: dict) -> dict:
        data = load_mock("actions.json")
        for action in data["actions"]:
            if action["id"] == action_id and action.get("user_id") == self.user_id:
                merged = copy.deepcopy(action)
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
        return {
            "run_id": str(uuid4()),
            "status": "queued",
            "message": "Email draft generation queued",
        }
