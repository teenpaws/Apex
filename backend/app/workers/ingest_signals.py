"""
Celery tasks for signal ingestion.

Each task fetches raw signal events from one external source, deduplicates
them against the signals table, and persists new records.

Deduplication strategy:
    dedup_hash = SHA-256( "{source}:{external_id}:{signal_date.date()}" )
    A signal is skipped if its dedup_hash already exists in the signals table.

All tasks return a summary dict:
    {"ingested": int, "duplicates": int, "errors": int}

Mock mode (USE_MOCK_DATA=true):
    No DB writes occur.  The task logs what it *would* write and returns
    counts based on the mock fixture data so the full pipeline can be
    exercised without a live Supabase project.

Circular import guard:
    celery_app is imported lazily inside each task body (and inside
    _get_celery_app()) rather than at module top-level, avoiding the chain:
        celery_app → include["app.workers.ingest_signals"] → import celery_app
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only used for type annotations — never executed at runtime.
    from app.core.celery_app import celery_app as _CeleryAppType  # noqa: F401

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_dedup_hash(source: str, external_id: str, signal_date: datetime) -> str:
    """
    Return a stable SHA-256 hex string for a (source, external_id, date) triple.

    Using only the *date* component (not full datetime) means the same article
    ingested twice within the same day is correctly identified as a duplicate
    even if timestamps differ slightly between API calls.
    """
    date_str = signal_date.date().isoformat()
    raw = f"{source}:{external_id}:{date_str}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _mock_ingest_result(events: list) -> dict[str, int]:
    """Log and return a mock-mode result without writing to the database."""
    for event in events:
        logger.info(
            "[MOCK] Would ingest signal: source=%r company=%r title=%r",
            event.source,
            event.company_name,
            (event.title or "")[:80],
        )
    return {"ingested": len(events), "duplicates": 0, "errors": 0}


def _resolve_company_uuid(company_id: str | None) -> uuid.UUID | None:
    """
    Parse *company_id* as a UUID, returning None on failure.

    Mock company IDs (e.g. ``co-00000-0000-…``) are not valid UUIDs, so
    this always returns None in mock mode — which is acceptable because
    no DB writes happen in that mode anyway.
    """
    if not company_id:
        return None
    try:
        return uuid.UUID(company_id)
    except (ValueError, AttributeError):
        return None


async def _persist_events(
    events: list,
    user_id: str,
    company_id: str | None,
    *,
    use_mock: bool,
) -> dict[str, int]:
    """
    Deduplicate and persist a list of SignalEvent objects to the DB.

    Returns:
        {"ingested": int, "duplicates": int, "errors": int}
    """
    if use_mock:
        return _mock_ingest_result(events)

    # Fast-path: nothing to do.
    if not events:
        return {"ingested": 0, "duplicates": 0, "errors": 0}

    # Live path — raw asyncpg (avoids psycopg2/pgvector ORM type issues).
    try:
        import asyncpg  # noqa: PLC0415
        import json as _json  # noqa: PLC0415
        from app.core.config import get_settings  # noqa: PLC0415
        from app.db.session import get_asyncpg_db_url  # noqa: PLC0415
        from app.models.enums import SignalType  # noqa: PLC0415
    except ImportError as exc:
        logger.error("DB imports unavailable — cannot persist signals: %s", exc)
        return {"ingested": 0, "duplicates": 0, "errors": len(events)}

    settings = get_settings()
    db_url = get_asyncpg_db_url()

    ingested = 0
    duplicates = 0
    errors = 0

    resolved_company_id = _resolve_company_uuid(company_id)

    # Parse user_id to UUID; "system" (beat scheduler) uses the seeded user.
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        user_uuid = uuid.uuid4()

    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        for event in events:
            try:
                dedup_hash = _make_dedup_hash(
                    event.source, event.external_id, event.signal_date
                )

                # Duplicate check
                existing = await conn.fetchval(
                    "SELECT id FROM signals WHERE dedup_hash = $1",
                    dedup_hash,
                )
                if existing is not None:
                    duplicates += 1
                    logger.debug(
                        "Duplicate skipped: hash=%s source=%r",
                        dedup_hash[:16],
                        event.source,
                    )
                    continue

                # Infer signal type from raw_data tag set by the client
                raw_type: str | None = (event.raw_data or {}).get("_signal_type")
                try:
                    signal_type = SignalType(raw_type) if raw_type else SignalType.FUNDING
                except ValueError:
                    signal_type = SignalType.FUNDING

                # Explicit INSERT — omits embedding column (populated by Phase 4)
                await conn.execute(
                    """
                    INSERT INTO signals
                        (id, user_id, company_id, type, source, title,
                         description, raw_data_json, signal_date,
                         is_duplicate, dedup_hash)
                    VALUES
                        ($1, $2, $3, $4, $5, $6,
                         $7, $8::jsonb, $9,
                         $10, $11)
                    """,
                    uuid.uuid4(),
                    user_uuid,
                    resolved_company_id,
                    signal_type.value,
                    event.source,
                    (event.title or "")[:500] or None,
                    (event.description or "")[:2000] or None,
                    _json.dumps(event.raw_data or {}),
                    event.signal_date,
                    False,
                    dedup_hash,
                )
                ingested += 1
                logger.info(
                    "Signal ingested: source=%r company=%r hash=%s",
                    event.source,
                    event.company_name,
                    dedup_hash[:16],
                )

            except Exception as exc:  # noqa: BLE001
                errors += 1
                logger.error(
                    "Failed to persist signal from source=%r: %s",
                    getattr(event, "source", "unknown"),
                    exc,
                )
    finally:
        await conn.close()

    return {"ingested": ingested, "duplicates": duplicates, "errors": errors}


# ── Internal async implementations ────────────────────────────────────────────
#
# Each _run_* coroutine contains the real async logic.  The Celery tasks below
# call asyncio.run(_run_*(...)) to bridge the sync Celery task boundary.
# This also makes the business logic trivially testable without a Celery broker.

async def _get_companies_from_db() -> list[dict]:
    """
    Fetch all companies from the DB.

    Returns a list of ``{"id": str, "name": str}`` dicts, or an empty list
    on any DB error (so the worker degrades gracefully rather than crashing).
    """
    try:
        import asyncpg  # noqa: PLC0415
        from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

        db_url = get_asyncpg_db_url()
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            rows = await conn.fetch(
                "SELECT id::text, name FROM companies ORDER BY name"
            )
            return [{"id": row["id"], "name": row["name"]} for row in rows]
        finally:
            await conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.error("_get_companies_from_db failed: %s", exc)
        return []


async def _run_newsdata(
    user_id: str,
    company_ids: list[str],
    company_name_map: dict[str, str] | None = None,
) -> dict[str, int]:
    """
    Ingest NewsData.io signals for every company in *company_ids*.

    *company_name_map* (optional): ``{company_id: company_name}``.  When
    provided (live mode) the API is queried by real company name rather than
    the raw UUID string, and the correct UUID is stored in the signal row.
    Without it (mock mode), the ``company_id`` string is used as-is.
    """
    from app.core.config import get_settings  # noqa: PLC0415
    from app.integrations.newsdata_client import NewsDataClient  # noqa: PLC0415

    settings = get_settings()
    client = NewsDataClient()
    totals: dict[str, int] = {"ingested": 0, "duplicates": 0, "errors": 0}

    for company_id in company_ids:
        company_name = (company_name_map or {}).get(company_id, company_id)
        events = await client.fetch_company_news(company_name)
        result = await _persist_events(
            events, user_id, company_id, use_mock=settings.USE_MOCK_DATA
        )
        for k in totals:
            totals[k] += result.get(k, 0)

    return totals


async def _run_gnews(
    user_id: str,
    company_ids: list[str],
    company_name_map: dict[str, str] | None = None,
) -> dict[str, int]:
    """
    Ingest GNews signals for every company in *company_ids*.

    See :func:`_run_newsdata` for *company_name_map* semantics.
    """
    from app.core.config import get_settings  # noqa: PLC0415
    from app.integrations.gnews_client import GNewsClient  # noqa: PLC0415

    settings = get_settings()
    client = GNewsClient()
    totals: dict[str, int] = {"ingested": 0, "duplicates": 0, "errors": 0}

    for company_id in company_ids:
        company_name = (company_name_map or {}).get(company_id, company_id)
        events = await client.fetch_company_news(company_name)
        result = await _persist_events(
            events, user_id, company_id, use_mock=settings.USE_MOCK_DATA
        )
        for k in totals:
            totals[k] += result.get(k, 0)

    return totals


async def _run_sec_edgar(
    user_id: str,
    company_ids: list[str],
    company_name_map: dict[str, str] | None = None,
) -> dict[str, int]:
    """
    Ingest SEC EDGAR (Form D + 8-K) filings for every company in *company_ids*.

    SEC EDGAR is US-only and searches by company name, so *company_name_map*
    is used the same way as in :func:`_run_newsdata`.
    """
    from app.core.config import get_settings  # noqa: PLC0415
    from app.integrations.sec_edgar_client import SECEdgarClient  # noqa: PLC0415

    settings = get_settings()
    client = SECEdgarClient()
    totals: dict[str, int] = {"ingested": 0, "duplicates": 0, "errors": 0}

    for company_id in company_ids:
        company_name = (company_name_map or {}).get(company_id, company_id)
        form_d_events = await client.fetch_form_d(company_name)
        k8_events = await client.fetch_8k_filings(company_name)
        result = await _persist_events(
            form_d_events + k8_events,
            user_id,
            company_id,
            use_mock=settings.USE_MOCK_DATA,
        )
        for k in totals:
            totals[k] += result.get(k, 0)

    return totals


async def _run_rss(user_id: str, feed_urls: list[str]) -> dict[str, int]:
    from urllib.parse import urlparse  # noqa: PLC0415
    from app.core.config import get_settings  # noqa: PLC0415
    from app.integrations.rss_client import RSSClient  # noqa: PLC0415

    settings = get_settings()
    client = RSSClient()
    totals: dict[str, int] = {"ingested": 0, "duplicates": 0, "errors": 0}

    for feed_url in feed_urls:
        parsed = urlparse(feed_url)
        company_name = parsed.netloc or feed_url
        events = await client.fetch_feed(feed_url, company_name)
        result = await _persist_events(
            events, user_id, None, use_mock=settings.USE_MOCK_DATA
        )
        for k in totals:
            totals[k] += result.get(k, 0)

    return totals


# ── Celery task registration ───────────────────────────────────────────────────
#
# Tasks are registered using a factory function to avoid the circular import
# that would occur if we used @celery_app.task at module level.

def _register_tasks(app) -> None:  # type: ignore[no-untyped-def]
    """Attach all ingest Celery tasks to *app*."""
    import asyncio  # noqa: PLC0415

    @app.task(name="app.workers.ingest_signals.ingest_from_newsdata", bind=True)
    def ingest_from_newsdata(self, user_id: str, company_ids: list[str]) -> dict:
        """
        Ingest signals for *company_ids* from NewsData.io (primary news source).

        Returns ``{"ingested": N, "duplicates": N, "errors": N}``.
        """
        result = asyncio.run(_run_newsdata(user_id, company_ids))
        logger.info("ingest_from_newsdata complete: %s", result)
        return result

    @app.task(name="app.workers.ingest_signals.ingest_from_gnews", bind=True)
    def ingest_from_gnews(self, user_id: str, company_ids: list[str]) -> dict:
        """
        Ingest signals for *company_ids* from GNews (backup news source).

        Should be called when NewsData.io quota is exhausted (returns empty list).
        """
        result = asyncio.run(_run_gnews(user_id, company_ids))
        logger.info("ingest_from_gnews complete: %s", result)
        return result

    @app.task(name="app.workers.ingest_signals.ingest_from_sec_edgar", bind=True)
    def ingest_from_sec_edgar(self, user_id: str, company_ids: list[str]) -> dict:
        """
        Ingest Form D (funding) + 8-K (exec hire / M&A) filings from SEC EDGAR.

        Observes the 10 req/s SEC rate limit (enforced inside SECEdgarClient).
        No API key required.
        """
        result = asyncio.run(_run_sec_edgar(user_id, company_ids))
        logger.info("ingest_from_sec_edgar complete: %s", result)
        return result

    @app.task(name="app.workers.ingest_signals.ingest_from_rss", bind=True)
    def ingest_from_rss(self, user_id: str, feed_urls: list[str]) -> dict:
        """
        Ingest signals from one or more RSS/Atom feed URLs.

        company_name for each feed is derived from the URL domain.
        Pass curated feed URLs associated with the user's tracked companies.
        """
        result = asyncio.run(_run_rss(user_id, feed_urls))
        logger.info("ingest_from_rss complete: %s", result)
        return result

    @app.task(name="app.workers.ingest_signals.ingest_all_sources", bind=True)
    def ingest_all_sources(self, user_id: str) -> dict:
        """
        Orchestrate ingestion from all four sources.

        This is the task triggered by Celery Beat every 4 hours.
        In mock mode it uses a hard-coded company list; in live mode it
        reads the user's tracked companies from the DB (Phase 4).
        """
        from app.core.config import get_settings  # noqa: PLC0415

        settings = get_settings()

        if settings.USE_MOCK_DATA:
            company_ids: list[str] = [
                "co-00000-0000-0000-000000000001",
                "co-00000-0000-0000-000000000002",
            ]
            feed_urls: list[str] = ["https://mock-company-blog.example.com/rss"]
            company_name_map: dict[str, str] | None = None  # mock: IDs used as names
        else:
            # Live mode: look up real company names from the DB so API clients
            # can search by name and signals are stored with correct company UUIDs.
            companies = asyncio.run(_get_companies_from_db())
            if not companies:
                logger.warning(
                    "ingest_all_sources: no companies found in DB — nothing to ingest. "
                    "Run 'python -m app.db.seeds.seed_production' to seed target companies."
                )
                return {"ingested": 0, "duplicates": 0, "errors": 0}

            company_ids = [c["id"] for c in companies]
            company_name_map = {c["id"]: c["name"] for c in companies}
            feed_urls = []  # RSS per-company feeds — Phase 4
            logger.info(
                "ingest_all_sources: ingesting for %d companies: %s",
                len(companies),
                [c["name"] for c in companies[:5]],  # log first 5 for brevity
            )

        totals: dict[str, int] = {"ingested": 0, "duplicates": 0, "errors": 0}

        source_tasks = [
            ("newsdata",  lambda: asyncio.run(_run_newsdata(user_id, company_ids, company_name_map))),
            ("gnews",     lambda: asyncio.run(_run_gnews(user_id, company_ids, company_name_map))),
            ("sec_edgar", lambda: asyncio.run(_run_sec_edgar(user_id, company_ids, company_name_map))),
            ("rss",       lambda: asyncio.run(_run_rss(user_id, feed_urls))),
        ]

        for source_name, run_fn in source_tasks:
            try:
                result = run_fn()
                for k in totals:
                    totals[k] += result.get(k, 0)
                logger.info(
                    "ingest_all_sources: %r → ingested=%d duplicates=%d errors=%d",
                    source_name,
                    result.get("ingested", 0),
                    result.get("duplicates", 0),
                    result.get("errors", 0),
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "ingest_all_sources: %r sub-task failed: %s", source_name, exc
                )
                totals["errors"] += 1

        logger.info("ingest_all_sources complete: %s", totals)
        return totals


# ── Bootstrap: register tasks when Celery app is importable ───────────────────

try:
    from app.core.celery_app import celery_app as _celery_app  # noqa: PLC0415
    _register_tasks(_celery_app)
    logger.debug("ingest_signals: Celery tasks registered.")
    # Expose tasks as module-level names for direct import in tests/callers
    ingest_from_newsdata = _celery_app.tasks["app.workers.ingest_signals.ingest_from_newsdata"]
    ingest_from_gnews = _celery_app.tasks["app.workers.ingest_signals.ingest_from_gnews"]
    ingest_from_sec_edgar = _celery_app.tasks["app.workers.ingest_signals.ingest_from_sec_edgar"]
    ingest_from_rss = _celery_app.tasks["app.workers.ingest_signals.ingest_from_rss"]
    ingest_all_sources = _celery_app.tasks["app.workers.ingest_signals.ingest_all_sources"]
except Exception as _exc:  # noqa: BLE001
    # Celery broker not running (e.g. during tests or API server startup).
    # Provide simple sync fallbacks so imports don't crash.
    import asyncio as _asyncio  # noqa: PLC0415

    logger.warning(
        "ingest_signals: Celery task registration skipped (no broker?): %s", _exc
    )

    def ingest_from_newsdata(user_id: str, company_ids: list) -> dict:  # type: ignore[misc]
        return _asyncio.run(_run_newsdata(user_id, company_ids))

    def ingest_from_gnews(user_id: str, company_ids: list) -> dict:  # type: ignore[misc]
        return _asyncio.run(_run_gnews(user_id, company_ids))

    def ingest_from_sec_edgar(user_id: str, company_ids: list) -> dict:  # type: ignore[misc]
        return _asyncio.run(_run_sec_edgar(user_id, company_ids))

    def ingest_from_rss(user_id: str, feed_urls: list) -> dict:  # type: ignore[misc]
        return _asyncio.run(_run_rss(user_id, feed_urls))

    def ingest_all_sources(user_id: str = "system") -> dict:  # type: ignore[misc]
        totals: dict[str, int] = {"ingested": 0, "duplicates": 0, "errors": 0}
        company_ids = ["co-mock-1", "co-mock-2"]
        feed_urls: list[str] = []
        for run_fn, args in [
            (_run_newsdata, (user_id, company_ids)),
            (_run_gnews, (user_id, company_ids)),
            (_run_sec_edgar, (user_id, company_ids)),
            (_run_rss, (user_id, feed_urls)),
        ]:
            try:
                result = _asyncio.run(run_fn(*args))
                for k in totals:
                    totals[k] += result.get(k, 0)
            except Exception as exc:  # noqa: BLE001
                logger.error("ingest_all_sources fallback: %s", exc)
                totals["errors"] += 1
        return totals
