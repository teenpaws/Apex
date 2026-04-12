"""
NewsData.io API client — primary news signal source.

Replaces NewsAPI.org (free tier is localhost-only, unusable in production).
Free tier: 200 req/day, commercial use permitted, no article delay.
API docs: https://newsdata.io/documentation

Caching: each query result is cached 24h in Redis using key:
    newsdata:{sha256(company_name + days_back)}
Rate limit handling: 429 → log warning, return [] (never crash the worker).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import get_settings

__all__ = ["NewsDataClient", "SignalEvent"]

logger = logging.getLogger(__name__)

NEWSDATA_BASE_URL = "https://newsdata.io/api/1/news"
CACHE_TTL_SECONDS = 86_400  # 24 hours


@dataclass
class SignalEvent:
    """
    Normalised representation of a raw market signal from any source.

    This is an internal transport type — it is converted to a SignalCreate
    Pydantic schema before hitting the database.
    """

    source: str          # e.g. "newsdata", "gnews", "sec_edgar", "rss"
    external_id: str     # unique identifier for deduplication (URL or filing ID)
    title: str
    description: str
    raw_data: dict[str, Any]
    signal_date: datetime
    company_name: str    # the company we queried for


def _query_hash(company_name: str, days_back: int) -> str:
    """Return a stable SHA-256 hex string for a (company, days_back) pair."""
    key = f"{company_name.lower().strip()}:{days_back}"
    return hashlib.sha256(key.encode()).hexdigest()


def _redis_client() -> Any | None:
    """
    Return a Redis client or None if Redis is unavailable.

    Imported lazily so the module loads cleanly without a running Redis.
    """
    try:
        import redis

        settings = get_settings()
        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        client.ping()  # verify connection is alive
        return client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable — proceeding without cache: %s", exc)
        return None


def _cache_get(redis_client: Any | None, cache_key: str) -> list[dict] | None:
    """Return cached list from Redis or None if not found / Redis is down."""
    if redis_client is None:
        return None
    try:
        raw = redis_client.get(cache_key)
        if raw:
            return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis GET failed for key %s: %s", cache_key, exc)
    return None


def _cache_set(
    redis_client: Any | None,
    cache_key: str,
    data: list[dict],
    ttl: int = CACHE_TTL_SECONDS,
) -> None:
    """Write *data* to Redis with a TTL. Silently ignores Redis failures."""
    if redis_client is None:
        return
    try:
        redis_client.setex(cache_key, ttl, json.dumps(data))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis SETEX failed for key %s: %s", cache_key, exc)


def _parse_newsdata_date(pub_date: str | None) -> datetime:
    """Parse NewsData.io pubDate string → UTC datetime (fallback: now)."""
    if not pub_date:
        return datetime.now(tz=timezone.utc)
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(pub_date, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    logger.debug("Could not parse NewsData date %r — using now()", pub_date)
    return datetime.now(tz=timezone.utc)


def _articles_to_events(
    articles: list[dict], company_name: str
) -> list[SignalEvent]:
    """Convert raw NewsData.io article dicts to SignalEvent objects."""
    events: list[SignalEvent] = []
    for article in articles:
        link: str = article.get("link", "") or ""
        if not link:
            # No URL means we cannot deduplicate — skip
            continue
        events.append(
            SignalEvent(
                source="newsdata",
                external_id=link,
                title=article.get("title", "") or "",
                description=article.get("description", "") or "",
                raw_data=article,
                signal_date=_parse_newsdata_date(article.get("pubDate")),
                company_name=company_name,
            )
        )
    return events


class NewsDataClient:
    """
    Async client for the NewsData.io REST API.

    Usage::

        client = NewsDataClient()
        events = await client.fetch_company_news("Stripe", days_back=7)
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def fetch_company_news(
        self,
        company_name: str,
        days_back: int = 7,
    ) -> list[SignalEvent]:
        """
        Fetch recent news articles about *company_name*.

        Returns an empty list on rate-limit (429) or any unrecoverable error
        so the Celery worker is never crashed by a single failing source.

        Results are cached for 24 hours in Redis (if available).
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_newsdata_events(company_name)

        cache_key = f"newsdata:{_query_hash(company_name, days_back)}"
        redis = _redis_client()

        cached = _cache_get(redis, cache_key)
        if cached is not None:
            logger.debug(
                "NewsData cache HIT for company=%r days_back=%d (%d articles)",
                company_name,
                days_back,
                len(cached),
            )
            return _articles_to_events(cached, company_name)

        from_date = (
            datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        ).strftime("%Y-%m-%d")

        params: dict[str, str] = {
            "apikey": self._settings.NEWSDATA_API_KEY,
            "q": company_name,
            "language": "en",
            "from_date": from_date,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(NEWSDATA_BASE_URL, params=params)

            if response.status_code == 429:
                logger.warning(
                    "NewsData.io rate limit (429) for company=%r — returning []",
                    company_name,
                )
                return []

            response.raise_for_status()
            payload: dict = response.json()

        except httpx.HTTPStatusError as exc:
            logger.error(
                "NewsData.io HTTP error %d for company=%r: %s",
                exc.response.status_code,
                company_name,
                exc,
            )
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "NewsData.io unexpected error for company=%r: %s",
                company_name,
                exc,
            )
            return []

        articles: list[dict] = payload.get("results", []) or []
        _cache_set(redis, cache_key, articles)

        logger.info(
            "NewsData.io fetched %d articles for company=%r",
            len(articles),
            company_name,
        )
        return _articles_to_events(articles, company_name)


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock_newsdata_events(company_name: str) -> list[SignalEvent]:
    """Return deterministic fixture events when USE_MOCK_DATA=true."""
    return [
        SignalEvent(
            source="newsdata",
            external_id=f"https://mock.newsdata.io/{company_name.lower().replace(' ', '-')}/funding-round",
            title=f"{company_name} raises $200M Series C to expand AI capabilities",
            description=(
                f"{company_name} has secured $200M in Series C funding led by Sequoia Capital, "
                "with plans to double its engineering team and expand into European markets."
            ),
            raw_data={
                "title": f"{company_name} raises $200M Series C to expand AI capabilities",
                "link": f"https://mock.newsdata.io/{company_name.lower().replace(' ', '-')}/funding-round",
                "pubDate": "2026-04-11 10:00:00",
                "source_id": "techcrunch",
                "description": f"{company_name} secures growth capital.",
            },
            signal_date=datetime(2026, 4, 11, 10, 0, 0, tzinfo=timezone.utc),
            company_name=company_name,
        )
    ]
