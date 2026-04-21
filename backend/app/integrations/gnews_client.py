"""
GNews API client — backup news signal source.

Activated when NewsData.io daily quota (200 req/day) is exhausted.
Free tier: 100 req/day.
API docs: https://gnews.io/docs/v4

Shares the same SignalEvent output schema as newsdata_client so the worker
can call either client transparently.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.integrations.newsdata_client import SignalEvent

__all__ = ["GNewsClient"]

logger = logging.getLogger(__name__)

GNEWS_BASE_URL = "https://gnews.io/api/v4/search"
MAX_RESULTS = 10


def _parse_gnews_date(published_at: str | None) -> datetime:
    """
    Parse GNews publishedAt string (ISO-8601) → UTC datetime.

    GNews returns strings like "2026-04-11T10:00:00Z".
    Fallback to now() if parsing fails.
    """
    if not published_at:
        return datetime.now(tz=timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(published_at, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    logger.debug("Could not parse GNews date %r — using now()", published_at)
    return datetime.now(tz=timezone.utc)


def _articles_to_events(
    articles: list[dict], company_name: str
) -> list[SignalEvent]:
    """Convert raw GNews article dicts to SignalEvent objects."""
    events: list[SignalEvent] = []
    for article in articles:
        url: str = article.get("url", "") or ""
        if not url:
            continue
        source_name: str = (
            (article.get("source") or {}).get("name", "") or "gnews"
        )
        events.append(
            SignalEvent(
                source="gnews",
                external_id=url,
                title=article.get("title", "") or "",
                description=article.get("description", "") or "",
                raw_data={**article, "_source_name": source_name},
                signal_date=_parse_gnews_date(article.get("publishedAt")),
                company_name=company_name,
            )
        )
    return events


class GNewsClient:
    """
    Async client for the GNews API (backup news source).

    Usage::

        client = GNewsClient()
        events = await client.fetch_company_news("OpenAI", days_back=7)

    Returns an empty list on 429 or any unrecoverable error — the caller
    (Celery worker) decides whether to fall through to the next source.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def fetch_company_news(
        self,
        company_name: str,
        days_back: int = 7,
    ) -> list[SignalEvent]:
        """
        Fetch recent news articles about *company_name* from GNews.

        GNews uses a ``from`` date filter expressed as an ISO-8601 datetime
        string (e.g. ``2026-04-04T00:00:00Z``).
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_gnews_events(company_name)

        from_dt = (
            datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        params: dict[str, str | int] = {
            "token": self._settings.GNEWS_API_KEY,
            "q": company_name,
            "lang": "en",
            "max": MAX_RESULTS,
            "from": from_dt,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(GNEWS_BASE_URL, params=params)

            if response.status_code == 429:
                logger.warning(
                    "GNews rate limit (429) for company=%r — returning []",
                    company_name,
                )
                return []

            response.raise_for_status()
            payload: dict = response.json()

        except httpx.HTTPStatusError as exc:
            logger.error(
                "GNews HTTP error %d for company=%r: %s",
                exc.response.status_code,
                company_name,
                exc,
            )
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "GNews unexpected error for company=%r: %s",
                company_name,
                exc,
            )
            return []

        articles: list[dict] = payload.get("articles", []) or []
        if not articles:
            logger.warning(
                "Source %r returned 0 articles for company=%r — check key/quota/connectivity",
                "gnews",
                company_name,
            )
        logger.info(
            "GNews fetched %d articles for company=%r",
            len(articles),
            company_name,
        )
        return _articles_to_events(articles, company_name)


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock_gnews_events(company_name: str) -> list[SignalEvent]:
    """Return deterministic fixture events when USE_MOCK_DATA=true."""
    slug = company_name.lower().replace(" ", "-")
    return [
        SignalEvent(
            source="gnews",
            external_id=f"https://mock.gnews.io/{slug}/exec-hire",
            title=f"{company_name} appoints new Chief AI Officer",
            description=(
                f"{company_name} has named Dr. Sarah Chen as Chief AI Officer, "
                "signalling a major push into enterprise AI product development."
            ),
            raw_data={
                "title": f"{company_name} appoints new Chief AI Officer",
                "url": f"https://mock.gnews.io/{slug}/exec-hire",
                "publishedAt": "2026-04-10T14:00:00Z",
                "source": {"name": "TechCrunch", "url": "https://techcrunch.com"},
                "description": f"{company_name} executive hire signals AI expansion.",
            },
            signal_date=datetime(2026, 4, 10, 14, 0, 0, tzinfo=timezone.utc),
            company_name=company_name,
        )
    ]
