"""
SignalService — business logic for market intelligence signals.

In mock mode (use_mock=True): serves data from mock_responses/signals.json.
In live mode: queries Supabase via asyncpg (pgbouncer-compatible).
"""

from __future__ import annotations

import logging
from uuid import uuid4

from app.core.errors import ApexHTTPException
from app.services._mock_loader import load_mock

logger = logging.getLogger(__name__)


class SignalService:
    """Service layer for signal read and ingest operations."""

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    async def list_signals(
        self,
        page: int = 1,
        page_size: int = 20,
        signal_type: str | None = None,
        company_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        if self.use_mock:
            return self._list_signals_mock(
                page=page,
                page_size=page_size,
                signal_type=signal_type,
                company_id=company_id,
            )
        return await self._live_list(
            page=page,
            page_size=page_size,
            signal_type=signal_type,
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def _live_list(
        self,
        page: int,
        page_size: int,
        signal_type: str | None,
        company_id: str | None,
        date_from: str | None,
        date_to: str | None,
    ) -> dict:
        import asyncpg
        import uuid
        from app.db.session import get_asyncpg_db_url

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            conditions = ['s.user_id = $1']
            args: list = [uuid.UUID(self.user_id)]
            idx = 2

            if signal_type:
                conditions.append(f's.type = ${idx}')
                args.append(signal_type.upper())
                idx += 1
            if company_id:
                conditions.append(f's.company_id = ${idx}')
                args.append(uuid.UUID(company_id))
                idx += 1
            if date_from:
                conditions.append(f's.signal_date >= ${idx}')
                args.append(date_from)
                idx += 1
            if date_to:
                conditions.append(f's.signal_date <= ${idx}')
                args.append(date_to)
                idx += 1

            where = ' AND '.join(conditions)

            count_row = await conn.fetchrow(
                f'SELECT COUNT(*) as cnt FROM signals s WHERE {where}',
                *args
            )
            total = count_row['cnt']

            offset = (page - 1) * page_size
            rows = await conn.fetch(
                f'''SELECT s.id, s.user_id, s.company_id, s.type, s.source,
                           s.title, s.description, s.signal_date,
                           s.relevance_score, s.processed_at, s.created_at,
                           c.name as company_name
                    FROM signals s
                    JOIN companies c ON c.id = s.company_id
                    WHERE {where}
                    ORDER BY s.signal_date DESC, s.created_at DESC
                    LIMIT ${idx} OFFSET ${idx+1}''',
                *args, page_size, offset
            )

            items = []
            for r in rows:
                items.append({
                    'id': str(r['id']),
                    'user_id': str(r['user_id']),
                    'company_id': str(r['company_id']),
                    'type': r['type'],
                    'source': r['source'],
                    'title': r['title'] or '',
                    'description': r['description'] or '',
                    'signal_date': r['signal_date'].isoformat() if r['signal_date'] else None,
                    'relevance_score': float(r['relevance_score'] or 0),
                    'processed_at': r['processed_at'].isoformat() if r['processed_at'] else None,
                    'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                    # UI aliases
                    'company': r['company_name'],
                    'date': r['signal_date'].isoformat() if r['signal_date'] else None,
                    'linkedOpportunityIds': [],
                })

            return {'data': items, 'total': total, 'page': page, 'per_page': page_size}
        finally:
            await conn.close()

    def _list_signals_mock(
        self,
        page: int,
        page_size: int,
        signal_type: str | None,
        company_id: str | None,
    ) -> dict:
        data = load_mock("signals.json")
        signals: list[dict] = data["signals"]

        signals = [s for s in signals if s.get("user_id") == self.user_id or self.user_id == "mock-user-id"]

        if signal_type is not None:
            signals = [s for s in signals if s.get("type") == signal_type.upper()]

        if company_id is not None:
            signals = [s for s in signals if s.get("company_id") == company_id]

        total = len(signals)
        start = (page - 1) * page_size
        end = start + page_size
        page_signals = signals[start:end]

        return {
            "data": page_signals,
            "total": total,
            "page": page,
            "per_page": page_size,
        }

    async def get_signal(self, signal_id: str) -> dict:
        if self.use_mock:
            return self._get_signal_mock(signal_id)
        return await self._live_get(signal_id)

    async def _live_get(self, signal_id: str) -> dict:
        import asyncpg
        import uuid
        from app.db.session import get_asyncpg_db_url

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                '''SELECT s.id, s.user_id, s.company_id, s.type, s.source,
                          s.title, s.description, s.signal_date,
                          s.relevance_score, s.processed_at, s.created_at,
                          c.name as company_name
                   FROM signals s
                   JOIN companies c ON c.id = s.company_id
                   WHERE s.id = $1 AND s.user_id = $2''',
                uuid.UUID(signal_id), uuid.UUID(self.user_id)
            )
            if not row:
                raise ApexHTTPException(404, "Signal not found", code="NOT_FOUND")
            return {
                'id': str(row['id']),
                'user_id': str(row['user_id']),
                'company_id': str(row['company_id']),
                'type': row['type'],
                'source': row['source'],
                'title': row['title'] or '',
                'description': row['description'] or '',
                'signal_date': row['signal_date'].isoformat() if row['signal_date'] else None,
                'relevance_score': float(row['relevance_score'] or 0),
                'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None,
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'company': row['company_name'],
                'date': row['signal_date'].isoformat() if row['signal_date'] else None,
                'linkedOpportunityIds': [],
            }
        finally:
            await conn.close()

    def _get_signal_mock(self, signal_id: str) -> dict:
        data = load_mock("signals.json")
        for signal in data["signals"]:
            if signal["id"] == signal_id:
                return signal
        raise ApexHTTPException(404, "Signal not found", code="NOT_FOUND")

    async def trigger_ingest(self, source: str | None = None) -> dict:
        run_id = str(uuid4())
        try:
            from app.workers.ingest_signals import ingest_all_sources  # noqa: PLC0415

            if hasattr(ingest_all_sources, "apply_async"):
                # Production: ingest_all_sources is a registered Celery task
                ingest_all_sources.apply_async(
                    kwargs={"user_id": self.user_id},
                    task_id=run_id,
                )
                logger.info(
                    "trigger_ingest: dispatched Celery task_id=%s user_id=%s",
                    run_id,
                    self.user_id,
                )
            else:
                # Dev fallback: no broker — run synchronously in a thread
                import asyncio  # noqa: PLC0415

                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, ingest_all_sources, self.user_id)
                logger.warning(
                    "trigger_ingest: Celery broker unavailable — running ingest directly "
                    "(task_id=%s)",
                    run_id,
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("trigger_ingest: failed to dispatch task: %s", exc)

        return {
            "run_id": run_id,
            "status": "queued",
            "message": "Signal ingestion queued",
        }
