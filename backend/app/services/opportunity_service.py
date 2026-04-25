"""
Opportunity service — business logic for predicted opportunities.

In mock mode (USE_MOCK_DATA=True) all operations are served from
backend/app/api/mock_responses/opportunities.json.

Live mode: queries Supabase via asyncpg (pgbouncer-compatible).
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
        if self.use_mock:
            return self._mock_list(
                page=page,
                page_size=page_size,
                confidence=confidence,
                status=status,
                company_id=company_id,
            )
        return await self._live_list(
            page=page,
            page_size=page_size,
            confidence=confidence,
            status=status,
            company_id=company_id,
        )

    async def _live_list(
        self,
        page: int,
        page_size: int,
        confidence: str | None,
        status: str | None,
        company_id: str | None,
    ) -> dict:
        import asyncpg
        import uuid
        from app.db.session import get_asyncpg_db_url

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            # Build filters
            conditions = ['o.user_id = $1']
            args: list = [uuid.UUID(self.user_id)]
            idx = 2

            if confidence:
                conditions.append(f'o.confidence = ${idx}')
                args.append(confidence.upper())
                idx += 1
            if status:
                conditions.append(f'o.status = ${idx}')
                args.append(status.upper())
                idx += 1
            if company_id:
                conditions.append(f'o.company_id = ${idx}')
                args.append(uuid.UUID(company_id))
                idx += 1

            where = ' AND '.join(conditions)

            count_row = await conn.fetchrow(
                f'SELECT COUNT(*) as cnt FROM opportunities o WHERE {where}',
                *args
            )
            total = count_row['cnt']

            offset = (page - 1) * page_size
            rows = await conn.fetch(
                f'''SELECT o.id, o.user_id, o.company_id, o.predicted_role,
                           o.confidence, o.timeline_weeks, o.why_fit,
                           o.approach_angle, o.predicted_salary_range,
                           o.fit_score, o.signal_ids, o.status,
                           o.created_at, o.updated_at,
                           c.name as company_name
                    FROM opportunities o
                    JOIN companies c ON c.id = o.company_id
                    WHERE {where}
                    ORDER BY
                      CASE o.confidence WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                      o.created_at DESC
                    LIMIT ${idx} OFFSET ${idx+1}''',
                *args, page_size, offset
            )

            items = []
            for r in rows:
                items.append({
                    'id': str(r['id']),
                    'user_id': str(r['user_id']),
                    'company_id': str(r['company_id']),
                    'predicted_role': r['predicted_role'],
                    'confidence': r['confidence'],
                    'timeline_weeks': r['timeline_weeks'],
                    'why_fit': r['why_fit'],
                    'approach_angle': r['approach_angle'],
                    'predicted_salary_range': r['predicted_salary_range'] or '',
                    'fit_score': float(r['fit_score'] or 0),
                    'status': r['status'],
                    'signal_ids': [str(s) for s in (r['signal_ids'] or [])],
                    'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                    'updated_at': r['updated_at'].isoformat() if r['updated_at'] else None,
                    # UI aliases
                    'company': r['company_name'],
                    'role': r['predicted_role'],
                    'whyFit': r['why_fit'],
                    'timeline': f"{r['timeline_weeks']}w" if r['timeline_weeks'] else None,
                })

            return {'data': items, 'total': total, 'page': page, 'per_page': page_size}
        finally:
            await conn.close()

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
            "data": page_items,
            "total": total,
            "page": page,
            "per_page": page_size,
        }

    # ── Get single ────────────────────────────────────────────────────────────

    async def get_opportunity(self, opportunity_id: str) -> dict:
        if self.use_mock:
            return self._mock_get(opportunity_id)
        return await self._live_get(opportunity_id)

    async def _live_get(self, opportunity_id: str) -> dict:
        import asyncpg
        import uuid
        from app.db.session import get_asyncpg_db_url

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                '''SELECT o.id, o.user_id, o.company_id, o.predicted_role,
                          o.confidence, o.timeline_weeks, o.why_fit,
                          o.approach_angle, o.predicted_salary_range,
                          o.fit_score, o.signal_ids, o.status,
                          o.created_at, o.updated_at,
                          c.name as company_name
                   FROM opportunities o
                   JOIN companies c ON c.id = o.company_id
                   WHERE o.id = $1 AND o.user_id = $2''',
                uuid.UUID(opportunity_id), uuid.UUID(self.user_id)
            )
            if not row:
                raise ApexHTTPException(404, "Opportunity not found", code="OPPORTUNITY_NOT_FOUND")
            return {
                'id': str(row['id']),
                'user_id': str(row['user_id']),
                'company_id': str(row['company_id']),
                'predicted_role': row['predicted_role'],
                'confidence': row['confidence'],
                'timeline_weeks': row['timeline_weeks'],
                'why_fit': row['why_fit'],
                'approach_angle': row['approach_angle'],
                'predicted_salary_range': row['predicted_salary_range'] or '',
                'fit_score': float(row['fit_score'] or 0),
                'status': row['status'],
                'signal_ids': [str(s) for s in (row['signal_ids'] or [])],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                'company': row['company_name'],
                'role': row['predicted_role'],
                'whyFit': row['why_fit'],
                'timeline': f"{row['timeline_weeks']}w" if row['timeline_weeks'] else None,
            }
        finally:
            await conn.close()

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
        return {
            "run_id": str(uuid4()),
            "status": "queued",
            "message": "Opportunity re-scoring queued",
        }
