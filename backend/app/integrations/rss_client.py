"""
RSS/Atom feed client — parses company blog and press-release feeds.

feedparser is a synchronous library, so all parsing runs inside
``asyncio.get_event_loop().run_in_executor(None, ...)`` to avoid blocking
the event loop.

Feed URLs are passed in at call time (from settings or the caller). The
output uses the same SignalEvent dataclass as the other clients.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from app.core.config import get_settings
from app.integrations.newsdata_client import SignalEvent

__all__ = ["RSSClient"]

logger = logging.getLogger(__name__)


def _import_feedparser() -> Any:
    """
    Import feedparser lazily so a missing package gives a clear error at
    call time rather than at module import.
    """
    try:
        import feedparser  # type: ignore[import-untyped]
        return feedparser
    except ImportError as exc:
        raise ImportError(
            "feedparser is required for RSS ingestion. "
            "Install it with: pip install feedparser"
        ) from exc


def _parse_rss_date(entry: dict) -> datetime:
    """
    Extract a publish/update datetime from a feedparser entry dict.

    Tries (in order):
        1. ``published_parsed`` (struct_time)
        2. ``updated_parsed`` (struct_time)
        3. ``published`` (string, RFC-2822 or ISO-8601)
        4. Falls back to UTC now.
    """
    import time as time_mod

    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                ts = time_mod.mktime(parsed)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (TypeError, OverflowError, OSError):
                continue

    for key in ("published", "updated"):
        raw = entry.get(key, "")
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:  # noqa: BLE001
                continue

    return datetime.now(tz=timezone.utc)


def _entry_to_event(entry: dict, feed_url: str, company_name: str) -> SignalEvent | None:
    """
    Convert a single feedparser entry to a SignalEvent.

    Returns None if the entry lacks a stable URL (needed for deduplication).
    """
    link: str = entry.get("link", "") or ""
    if not link:
        return None

    title: str = entry.get("title", "") or ""
    # feedparser puts content in either .summary or .description
    description: str = (
        entry.get("summary", "")
        or entry.get("description", "")
        or ""
    )

    return SignalEvent(
        source="rss",
        external_id=link,
        title=title,
        description=description,
        raw_data={
            "feed_url": feed_url,
            "entry_id": entry.get("id", link),
            "tags": [t.get("term", "") for t in (entry.get("tags") or [])],
            "author": entry.get("author", ""),
        },
        signal_date=_parse_rss_date(entry),
        company_name=company_name,
    )


class RSSClient:
    """
    Async RSS/Atom feed client.

    Usage::

        client = RSSClient()
        events = await client.fetch_feed(
            "https://company.com/blog/rss.xml",
            company_name="Company Inc.",
        )
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def fetch_feed(
        self,
        feed_url: str,
        company_name: str,
    ) -> list[SignalEvent]:
        """
        Fetch and parse a single RSS/Atom feed URL.

        Parsing is offloaded to a thread executor so the async event loop is
        never blocked by feedparser's synchronous network I/O.

        Returns [] on any error so the worker is never crashed by a bad feed.
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_rss_events(feed_url, company_name)

        feedparser = _import_feedparser()

        loop = asyncio.get_event_loop()
        try:
            feed = await loop.run_in_executor(
                None,
                feedparser.parse,
                feed_url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "RSS parse error for feed=%r company=%r: %s",
                feed_url,
                company_name,
                exc,
            )
            return []

        # feedparser signals HTTP errors via bozo + bozo_exception
        if feed.get("bozo") and not feed.get("entries"):
            logger.warning(
                "RSS feed=%r returned bozo error: %s",
                feed_url,
                feed.get("bozo_exception"),
            )
            return []

        entries: list[dict] = feed.get("entries", []) or []
        events: list[SignalEvent] = []
        for entry in entries:
            event = _entry_to_event(entry, feed_url, company_name)
            if event is not None:
                events.append(event)

        logger.info(
            "RSS fetched %d entries from feed=%r for company=%r",
            len(events),
            feed_url,
            company_name,
        )
        return events


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock_rss_events(feed_url: str, company_name: str) -> list[SignalEvent]:
    """Return deterministic RSS fixture event when USE_MOCK_DATA=true."""
    slug = company_name.lower().replace(" ", "-")
    return [
        SignalEvent(
            source="rss",
            external_id=f"https://{slug}.com/blog/new-york-office-expansion",
            title=f"{company_name} Opens New York Office to Support Rapid Growth",
            description=(
                f"{company_name} today announced the opening of its flagship New York office, "
                "adding 200 positions across engineering, sales, and operations teams."
            ),
            raw_data={
                "feed_url": feed_url,
                "entry_id": f"https://{slug}.com/blog/new-york-office-expansion",
                "tags": ["expansion", "hiring", "office"],
                "author": f"{company_name} Communications",
            },
            signal_date=datetime(2026, 4, 9, 12, 0, 0, tzinfo=timezone.utc),
            company_name=company_name,
        )
    ]
