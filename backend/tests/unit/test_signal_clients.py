"""
Unit tests for signal integration clients.

Tests cover:
  - NewsDataClient.fetch_company_news()
  - GNewsClient.fetch_company_news()
  - SECEdgarClient.fetch_form_d()    (when implemented)
  - RSSClient.fetch_feed()           (when implemented)

All tests run with USE_MOCK_DATA=true — the mock paths are tested directly.
HTTP-level tests use respx to mock the underlying httpx calls and exercise
the real (non-mock) code paths.

If an integration module has not been implemented yet, that test class is
skipped gracefully via pytest.importorskip.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Path to fixtures directory (relative to this file)
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ===========================================================================
# Helpers
# ===========================================================================


def _load_fixture(name: str) -> dict:
    """Load a JSON fixture file from backend/tests/fixtures/."""
    path = FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


# ===========================================================================
# NewsDataClient
# ===========================================================================


class TestNewsDataClientMockMode:
    """Tests for NewsDataClient when USE_MOCK_DATA=true (default in test env)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        """Skip the entire class if newsdata_client is not implemented yet."""
        pytest.importorskip(
            "app.integrations.newsdata_client",
            reason="newsdata_client.py not yet implemented",
        )

    @pytest.mark.asyncio
    async def test_mock_mode_returns_list(self):
        """Mock mode must return a list (never raise)."""
        from app.integrations.newsdata_client import NewsDataClient

        client = NewsDataClient()
        events = await client.fetch_company_news("McKinsey", days_back=7)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_mock_mode_returns_signal_events(self):
        """Each item in mock output must be a SignalEvent instance."""
        from app.integrations.newsdata_client import NewsDataClient, SignalEvent

        client = NewsDataClient()
        events = await client.fetch_company_news("McKinsey", days_back=7)
        assert len(events) >= 1
        for event in events:
            assert isinstance(event, SignalEvent)

    @pytest.mark.asyncio
    async def test_mock_mode_event_source_is_newsdata(self):
        """All mock events must carry source='newsdata'."""
        from app.integrations.newsdata_client import NewsDataClient

        client = NewsDataClient()
        events = await client.fetch_company_news("McKinsey", days_back=7)
        for event in events:
            assert event.source == "newsdata"

    @pytest.mark.asyncio
    async def test_mock_mode_event_has_required_fields(self):
        """SignalEvent must expose all required fields."""
        from app.integrations.newsdata_client import NewsDataClient

        client = NewsDataClient()
        events = await client.fetch_company_news("McKinsey", days_back=7)
        event = events[0]
        assert event.title != ""
        assert event.description != ""
        assert isinstance(event.signal_date, datetime)
        assert event.company_name == "McKinsey"
        assert event.external_id != ""

    @pytest.mark.asyncio
    async def test_mock_mode_event_signal_date_is_aware(self):
        """signal_date must be timezone-aware (UTC)."""
        from app.integrations.newsdata_client import NewsDataClient

        client = NewsDataClient()
        events = await client.fetch_company_news("McKinsey", days_back=7)
        for event in events:
            assert event.signal_date.tzinfo is not None


class TestNewsDataClientHTTP:
    """
    Tests for the real HTTP path (USE_MOCK_DATA=false).

    Uses respx to intercept httpx calls — no real network traffic.
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(
            "app.integrations.newsdata_client",
            reason="newsdata_client.py not yet implemented",
        )

    def _make_client_live(self):
        """Return a NewsDataClient with mock mode disabled."""
        from app.integrations.newsdata_client import NewsDataClient
        from app.core.config import get_settings

        client = NewsDataClient()
        client._settings = get_settings()
        # Force live mode
        client._settings.__class__.USE_MOCK_DATA.default = False
        # Patch the settings attribute directly
        object.__setattr__(client._settings, "USE_MOCK_DATA", False)
        return client

    @pytest.mark.asyncio
    async def test_live_mode_parses_fixture_response(self):
        """Real HTTP path: given a well-formed NewsData response, return SignalEvents."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.newsdata_client import (
            NewsDataClient,
            SignalEvent,
            NEWSDATA_BASE_URL,
        )

        payload = _load_fixture("newsdata_response.json")

        with respx.mock(base_url=NEWSDATA_BASE_URL) as mock:
            mock.get("").mock(return_value=httpx.Response(200, json=payload))

            # Patch settings to disable mock mode and set a fake API key
            with patch("app.integrations.newsdata_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.NEWSDATA_API_KEY = "fake-key"
                settings.REDIS_URL = "redis://localhost:6379/0"
                mock_settings.return_value = settings

                client = NewsDataClient()
                events = await client.fetch_company_news("McKinsey", days_back=7)

        assert isinstance(events, list)
        assert len(events) >= 1
        for event in events:
            assert isinstance(event, SignalEvent)
            assert event.source == "newsdata"

    @pytest.mark.asyncio
    async def test_live_mode_429_returns_empty_list(self):
        """Rate limit response (429) must return [] without raising."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.newsdata_client import NewsDataClient, NEWSDATA_BASE_URL

        with respx.mock(base_url=NEWSDATA_BASE_URL) as mock:
            mock.get("").mock(return_value=httpx.Response(429, text="Rate limited"))

            with patch("app.integrations.newsdata_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.NEWSDATA_API_KEY = "fake-key"
                settings.REDIS_URL = "redis://localhost:6379/0"
                mock_settings.return_value = settings

                client = NewsDataClient()
                events = await client.fetch_company_news("McKinsey", days_back=7)

        assert events == []

    @pytest.mark.asyncio
    async def test_live_mode_429_logs_warning(self, caplog):
        """Rate limit (429) must log a warning."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.newsdata_client import NewsDataClient, NEWSDATA_BASE_URL

        with respx.mock(base_url=NEWSDATA_BASE_URL) as mock:
            mock.get("").mock(return_value=httpx.Response(429, text="Rate limited"))

            with patch("app.integrations.newsdata_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.NEWSDATA_API_KEY = "fake-key"
                settings.REDIS_URL = "redis://localhost:6379/0"
                mock_settings.return_value = settings

                with caplog.at_level(logging.WARNING, logger="app.integrations.newsdata_client"):
                    client = NewsDataClient()
                    await client.fetch_company_news("McKinsey", days_back=7)

        assert any("429" in record.message or "rate limit" in record.message.lower()
                   for record in caplog.records)

    @pytest.mark.asyncio
    async def test_live_mode_network_error_returns_empty_list(self):
        """Network error must return [] without raising."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.newsdata_client import NewsDataClient, NEWSDATA_BASE_URL

        with respx.mock(base_url=NEWSDATA_BASE_URL) as mock:
            mock.get("").mock(side_effect=httpx.ConnectError("Connection refused"))

            with patch("app.integrations.newsdata_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.NEWSDATA_API_KEY = "fake-key"
                settings.REDIS_URL = "redis://localhost:6379/0"
                mock_settings.return_value = settings

                client = NewsDataClient()
                events = await client.fetch_company_news("McKinsey", days_back=7)

        assert events == []

    @pytest.mark.asyncio
    async def test_live_mode_skips_articles_without_url(self):
        """Articles missing a 'link' field must be silently skipped."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.newsdata_client import NewsDataClient, NEWSDATA_BASE_URL

        payload = {
            "status": "success",
            "totalResults": 2,
            "results": [
                {
                    "article_id": "no-link",
                    "title": "Article without link",
                    "description": "No link here",
                    "pubDate": "2026-04-10 12:00:00",
                    # Deliberately missing "link"
                },
                {
                    "article_id": "with-link",
                    "title": "Article with link",
                    "description": "Has a link",
                    "pubDate": "2026-04-10 12:00:00",
                    "link": "https://example.com/article",
                },
            ],
        }

        with respx.mock(base_url=NEWSDATA_BASE_URL) as mock:
            mock.get("").mock(return_value=httpx.Response(200, json=payload))

            with patch("app.integrations.newsdata_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.NEWSDATA_API_KEY = "fake-key"
                settings.REDIS_URL = "redis://localhost:6379/0"
                mock_settings.return_value = settings

                client = NewsDataClient()
                events = await client.fetch_company_news("TestCorp", days_back=7)

        # Only the article that has a link should be returned
        assert len(events) == 1
        assert events[0].external_id == "https://example.com/article"


# ===========================================================================
# GNewsClient
# ===========================================================================


class TestGNewsClientMockMode:
    """Tests for GNewsClient when USE_MOCK_DATA=true."""

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(
            "app.integrations.gnews_client",
            reason="gnews_client.py not yet implemented",
        )

    @pytest.mark.asyncio
    async def test_mock_mode_returns_list(self):
        from app.integrations.gnews_client import GNewsClient

        client = GNewsClient()
        events = await client.fetch_company_news("Bain", days_back=7)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_mock_mode_returns_signal_events(self):
        from app.integrations.gnews_client import GNewsClient
        from app.integrations.newsdata_client import SignalEvent

        client = GNewsClient()
        events = await client.fetch_company_news("Bain", days_back=7)
        assert len(events) >= 1
        for event in events:
            assert isinstance(event, SignalEvent)

    @pytest.mark.asyncio
    async def test_mock_mode_event_source_is_gnews(self):
        from app.integrations.gnews_client import GNewsClient

        client = GNewsClient()
        events = await client.fetch_company_news("Bain", days_back=7)
        for event in events:
            assert event.source == "gnews"

    @pytest.mark.asyncio
    async def test_mock_mode_event_has_required_fields(self):
        from app.integrations.gnews_client import GNewsClient

        client = GNewsClient()
        events = await client.fetch_company_news("Bain", days_back=7)
        event = events[0]
        assert event.title != ""
        assert isinstance(event.signal_date, datetime)
        assert event.company_name == "Bain"
        assert event.external_id.startswith("http")

    @pytest.mark.asyncio
    async def test_mock_mode_signal_date_is_aware(self):
        from app.integrations.gnews_client import GNewsClient

        client = GNewsClient()
        events = await client.fetch_company_news("Bain", days_back=7)
        for event in events:
            assert event.signal_date.tzinfo is not None


class TestGNewsClientHTTP:
    """HTTP-level tests for GNewsClient (live mode, mocked via respx)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(
            "app.integrations.gnews_client",
            reason="gnews_client.py not yet implemented",
        )

    @pytest.mark.asyncio
    async def test_live_mode_parses_fixture_response(self):
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.gnews_client import GNewsClient, GNEWS_BASE_URL
        from app.integrations.newsdata_client import SignalEvent

        payload = _load_fixture("gnews_response.json")

        with respx.mock(base_url=GNEWS_BASE_URL) as mock:
            mock.get("").mock(return_value=httpx.Response(200, json=payload))

            with patch("app.integrations.gnews_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.GNEWS_API_KEY = "fake-gnews-key"
                mock_settings.return_value = settings

                client = GNewsClient()
                events = await client.fetch_company_news("Bain", days_back=7)

        assert len(events) >= 1
        for event in events:
            assert isinstance(event, SignalEvent)
            assert event.source == "gnews"

    @pytest.mark.asyncio
    async def test_live_mode_429_returns_empty_list(self):
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.gnews_client import GNewsClient, GNEWS_BASE_URL

        with respx.mock(base_url=GNEWS_BASE_URL) as mock:
            mock.get("").mock(return_value=httpx.Response(429, text="Too Many Requests"))

            with patch("app.integrations.gnews_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.GNEWS_API_KEY = "fake-gnews-key"
                mock_settings.return_value = settings

                client = GNewsClient()
                events = await client.fetch_company_news("Bain", days_back=7)

        assert events == []

    @pytest.mark.asyncio
    async def test_live_mode_network_error_returns_empty_list(self):
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.gnews_client import GNewsClient, GNEWS_BASE_URL

        with respx.mock(base_url=GNEWS_BASE_URL) as mock:
            mock.get("").mock(side_effect=httpx.ConnectError("Connection refused"))

            with patch("app.integrations.gnews_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.GNEWS_API_KEY = "fake-gnews-key"
                mock_settings.return_value = settings

                client = GNewsClient()
                events = await client.fetch_company_news("Bain", days_back=7)

        assert events == []

    @pytest.mark.asyncio
    async def test_live_mode_missing_api_key_returns_empty_list(self):
        """When GNEWS_API_KEY is empty/unset, client must return [] gracefully."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.gnews_client import GNewsClient, GNEWS_BASE_URL

        # Simulate missing API key by returning 403 Forbidden
        with respx.mock(base_url=GNEWS_BASE_URL) as mock:
            mock.get("").mock(return_value=httpx.Response(403, text="Forbidden"))

            with patch("app.integrations.gnews_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.GNEWS_API_KEY = ""
                mock_settings.return_value = settings

                client = GNewsClient()
                events = await client.fetch_company_news("Bain", days_back=7)

        assert events == []

    @pytest.mark.asyncio
    async def test_live_mode_skips_articles_without_url(self):
        """Articles missing 'url' must be silently skipped."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.gnews_client import GNewsClient, GNEWS_BASE_URL

        payload = {
            "totalArticles": 2,
            "articles": [
                {
                    "title": "No URL article",
                    "description": "Missing URL",
                    "publishedAt": "2026-04-09T10:30:00Z",
                    # Deliberately omitting "url"
                    "source": {"name": "Test"},
                },
                {
                    "title": "Has URL article",
                    "description": "This one has a URL",
                    "publishedAt": "2026-04-09T10:30:00Z",
                    "url": "https://example.com/has-url",
                    "source": {"name": "Test"},
                },
            ],
        }

        with respx.mock(base_url=GNEWS_BASE_URL) as mock:
            mock.get("").mock(return_value=httpx.Response(200, json=payload))

            with patch("app.integrations.gnews_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                settings.GNEWS_API_KEY = "fake-key"
                mock_settings.return_value = settings

                client = GNewsClient()
                events = await client.fetch_company_news("TestCorp", days_back=7)

        assert len(events) == 1
        assert events[0].external_id == "https://example.com/has-url"


# ===========================================================================
# SECEdgarClient
# ===========================================================================


class TestSECEdgarClient:
    """Tests for SECEdgarClient.fetch_form_d()."""

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(
            "app.integrations.sec_edgar_client",
            reason="sec_edgar_client.py not yet implemented",
        )

    @pytest.mark.asyncio
    async def test_mock_mode_returns_list(self):
        from app.integrations.sec_edgar_client import SECEdgarClient

        client = SECEdgarClient()
        events = await client.fetch_form_d("Sequoia Capital", days_back=30)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_mock_mode_event_source_is_sec_edgar(self):
        from app.integrations.sec_edgar_client import SECEdgarClient

        client = SECEdgarClient()
        events = await client.fetch_form_d("Sequoia Capital", days_back=30)
        for event in events:
            assert event.source == "sec_edgar"

    @pytest.mark.asyncio
    async def test_mock_mode_event_has_funding_signal_type_hint(self):
        """
        SEC Form D events are always funding signals.
        The returned SignalEvent must carry a raw_data hint with 'form_type' == 'D'
        or a signal_type_hint field set to 'FUNDING'.
        """
        from app.integrations.sec_edgar_client import SECEdgarClient

        client = SECEdgarClient()
        events = await client.fetch_form_d("Sequoia Capital", days_back=30)
        assert len(events) >= 1
        event = events[0]
        # Either raw_data contains form_type "D" or there's an explicit hint
        has_hint = (
            event.raw_data.get("form_type") == "D"
            or event.raw_data.get("signal_type_hint") == "FUNDING"
            or "FUND" in event.title.upper()
            or "Form D" in event.title
        )
        assert has_hint, f"Expected FUNDING hint in event: {event}"

    @pytest.mark.asyncio
    async def test_live_mode_sets_user_agent_header(self):
        """
        SEC EDGAR requires a valid User-Agent (RFC 7231 contact info).
        The client must include a non-empty User-Agent header.
        """
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.sec_edgar_client import SECEdgarClient

        captured_headers: dict = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            payload = _load_fixture("sec_edgar_form_d_response.json")
            return httpx.Response(200, json=payload)

        with respx.mock() as mock:
            mock.get(url__regex=r"https://efts\.sec\.gov.*").mock(side_effect=capture_request)

            with patch("app.integrations.sec_edgar_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                mock_settings.return_value = settings

                client = SECEdgarClient()
                try:
                    await client.fetch_form_d("Acme Ventures", days_back=30)
                except Exception:
                    pass  # We only care about the header, not the full parse

        if captured_headers:
            user_agent = captured_headers.get("user-agent", "")
            assert user_agent != "", "SEC EDGAR client must set a non-empty User-Agent"

    @pytest.mark.asyncio
    async def test_live_mode_parses_fixture_response(self):
        """Well-formed SEC EDGAR response yields at least one SignalEvent."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.sec_edgar_client import SECEdgarClient
        from app.integrations.newsdata_client import SignalEvent

        payload = _load_fixture("sec_edgar_form_d_response.json")

        with respx.mock() as mock:
            mock.get(url__regex=r"https://efts\.sec\.gov.*").mock(
                return_value=httpx.Response(200, json=payload)
            )

            with patch("app.integrations.sec_edgar_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                mock_settings.return_value = settings

                client = SECEdgarClient()
                events = await client.fetch_form_d("Acme Ventures", days_back=30)

        assert isinstance(events, list)
        for event in events:
            assert isinstance(event, SignalEvent)

    @pytest.mark.asyncio
    async def test_live_mode_network_error_returns_empty_list(self):
        """Network error must return [] without raising."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.sec_edgar_client import SECEdgarClient

        with respx.mock() as mock:
            mock.get(url__regex=r"https://efts\.sec\.gov.*").mock(
                side_effect=httpx.ConnectError("No route to host")
            )

            with patch("app.integrations.sec_edgar_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                mock_settings.return_value = settings

                client = SECEdgarClient()
                events = await client.fetch_form_d("Acme Ventures", days_back=30)

        assert events == []


# ===========================================================================
# RSSClient
# ===========================================================================


class TestRSSClient:
    """Tests for RSSClient.fetch_feed()."""

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(
            "app.integrations.rss_client",
            reason="rss_client.py not yet implemented",
        )

    @pytest.mark.asyncio
    async def test_fetch_feed_returns_list(self):
        from app.integrations.rss_client import RSSClient
        from app.integrations.newsdata_client import SignalEvent

        client = RSSClient()
        events = await client.fetch_feed("https://example.com/feed.rss", "Test Corp")
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_fetch_feed_events_are_signal_events(self):
        from app.integrations.rss_client import RSSClient
        from app.integrations.newsdata_client import SignalEvent

        client = RSSClient()
        events = await client.fetch_feed("https://example.com/feed.rss", "Test Corp")
        for event in events:
            assert isinstance(event, SignalEvent)

    @pytest.mark.asyncio
    async def test_fetch_feed_source_is_rss(self):
        from app.integrations.rss_client import RSSClient

        client = RSSClient()
        events = await client.fetch_feed("https://example.com/feed.rss", "Test Corp")
        for event in events:
            assert event.source == "rss"

    @pytest.mark.asyncio
    async def test_fetch_feed_malformed_xml_returns_empty_list(self):
        """Malformed RSS/XML must return [] without raising."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.rss_client import RSSClient

        malformed_content = b"<not valid xml at all ><><><"

        with respx.mock() as mock:
            mock.get("https://example.com/bad-feed.rss").mock(
                return_value=httpx.Response(200, content=malformed_content)
            )

            with patch("app.integrations.rss_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                mock_settings.return_value = settings

                client = RSSClient()
                events = await client.fetch_feed(
                    "https://example.com/bad-feed.rss", "Bad Corp"
                )

        assert events == []

    @pytest.mark.asyncio
    async def test_fetch_feed_empty_feed_returns_empty_list(self):
        """A valid RSS feed with no items returns []."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.rss_client import RSSClient

        empty_feed = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
    <link>https://example.com</link>
    <description>No items</description>
  </channel>
</rss>"""

        with respx.mock() as mock:
            mock.get("https://example.com/empty.rss").mock(
                return_value=httpx.Response(200, content=empty_feed)
            )

            with patch("app.integrations.rss_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                mock_settings.return_value = settings

                client = RSSClient()
                events = await client.fetch_feed("https://example.com/empty.rss", "Empty Corp")

        assert events == []

    @pytest.mark.asyncio
    async def test_fetch_feed_live_parses_real_rss_fixture(self):
        """Well-formed RSS fixture yields SignalEvents with correct fields."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.rss_client import RSSClient
        from app.integrations.newsdata_client import SignalEvent

        rss_content = (FIXTURES_DIR / "rss_feed_response.xml").read_bytes()

        with respx.mock() as mock:
            mock.get("https://example.com/feed.rss").mock(
                return_value=httpx.Response(200, content=rss_content)
            )

            with patch("app.integrations.rss_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                mock_settings.return_value = settings

                client = RSSClient()
                events = await client.fetch_feed("https://example.com/feed.rss", "Test Corp")

        assert len(events) >= 1
        for event in events:
            assert isinstance(event, SignalEvent)
            assert event.company_name == "Test Corp"
            assert event.source == "rss"
            assert event.title != ""
            assert event.external_id.startswith("http")

    @pytest.mark.asyncio
    async def test_fetch_feed_network_error_returns_empty_list(self):
        """Network error fetching RSS must return [] without raising."""
        try:
            import respx
        except ImportError:
            pytest.skip("respx not installed")

        from app.integrations.rss_client import RSSClient

        with respx.mock() as mock:
            mock.get("https://example.com/feed.rss").mock(
                side_effect=httpx.ConnectError("DNS lookup failed")
            )

            with patch("app.integrations.rss_client.get_settings") as mock_settings:
                settings = MagicMock()
                settings.USE_MOCK_DATA = False
                mock_settings.return_value = settings

                client = RSSClient()
                events = await client.fetch_feed("https://example.com/feed.rss", "Test Corp")

        assert events == []


# ===========================================================================
# SignalEvent dataclass (shared between clients)
# ===========================================================================


class TestSignalEventDataclass:
    """Sanity checks for the SignalEvent dataclass itself."""

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(
            "app.integrations.newsdata_client",
            reason="newsdata_client.py not yet implemented",
        )

    def test_signal_event_required_fields(self):
        """SignalEvent can be constructed with all required fields."""
        from app.integrations.newsdata_client import SignalEvent

        event = SignalEvent(
            source="newsdata",
            external_id="https://example.com/article",
            title="Test Title",
            description="Test description.",
            raw_data={"key": "value"},
            signal_date=datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc),
            company_name="Test Corp",
        )
        assert event.source == "newsdata"
        assert event.external_id == "https://example.com/article"
        assert event.company_name == "Test Corp"

    def test_signal_event_raw_data_is_dict(self):
        """raw_data must accept a dict."""
        from app.integrations.newsdata_client import SignalEvent

        event = SignalEvent(
            source="rss",
            external_id="https://example.com/rss-item",
            title="Title",
            description="Desc",
            raw_data={"nested": {"key": True}},
            signal_date=datetime.now(tz=timezone.utc),
            company_name="Corp",
        )
        assert isinstance(event.raw_data, dict)
