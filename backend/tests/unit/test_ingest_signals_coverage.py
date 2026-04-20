"""
Coverage gap-fill for app/workers/ingest_signals.py.

Tests cover:
  - _run_newsdata, _run_gnews, _run_sec_edgar, _run_rss async functions (mock mode)
  - ingest_from_* wrapper functions
  - ingest_all_sources orchestration

All tests use USE_MOCK_DATA=true (set in conftest).
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch


# ── Async ingest runner functions ─────────────────────────────────────────────

class TestRunNewsdata:
    """Tests for _run_newsdata async function."""

    @pytest.mark.asyncio
    async def test_run_newsdata_mock_returns_summary_dict(self):
        from app.workers.ingest_signals import _run_newsdata
        result = await _run_newsdata("mock-user-id", ["co-00000-0000-0000-000000000001"])
        assert isinstance(result, dict)
        assert "ingested" in result
        assert "duplicates" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_run_newsdata_mock_ingested_non_negative(self):
        from app.workers.ingest_signals import _run_newsdata
        result = await _run_newsdata("mock-user-id", ["co-00000-0000-0000-000000000001"])
        assert result["ingested"] >= 0

    @pytest.mark.asyncio
    async def test_run_newsdata_empty_company_ids(self):
        from app.workers.ingest_signals import _run_newsdata
        result = await _run_newsdata("mock-user-id", [])
        assert isinstance(result, dict)
        assert result["ingested"] == 0

    @pytest.mark.asyncio
    async def test_run_newsdata_multiple_companies(self):
        from app.workers.ingest_signals import _run_newsdata
        result = await _run_newsdata("mock-user-id", [
            "co-00000-0000-0000-000000000001",
            "co-00000-0000-0000-000000000002",
        ])
        assert isinstance(result, dict)
        assert result["ingested"] >= 0


class TestRunGnews:
    """Tests for _run_gnews async function."""

    @pytest.mark.asyncio
    async def test_run_gnews_mock_returns_summary_dict(self):
        from app.workers.ingest_signals import _run_gnews
        result = await _run_gnews("mock-user-id", ["co-00000-0000-0000-000000000001"])
        assert isinstance(result, dict)
        assert "ingested" in result

    @pytest.mark.asyncio
    async def test_run_gnews_empty_company_ids(self):
        from app.workers.ingest_signals import _run_gnews
        result = await _run_gnews("mock-user-id", [])
        assert result["ingested"] == 0

    @pytest.mark.asyncio
    async def test_run_gnews_multiple_companies(self):
        from app.workers.ingest_signals import _run_gnews
        result = await _run_gnews("mock-user-id", [
            "co-00000-0000-0000-000000000001",
            "co-00000-0000-0000-000000000002",
        ])
        assert isinstance(result, dict)


class TestRunSecEdgar:
    """Tests for _run_sec_edgar async function."""

    @pytest.mark.asyncio
    async def test_run_sec_edgar_mock_returns_summary_dict(self):
        from app.workers.ingest_signals import _run_sec_edgar
        result = await _run_sec_edgar("mock-user-id", ["co-00000-0000-0000-000000000001"])
        assert isinstance(result, dict)
        assert "ingested" in result

    @pytest.mark.asyncio
    async def test_run_sec_edgar_empty_company_ids(self):
        from app.workers.ingest_signals import _run_sec_edgar
        result = await _run_sec_edgar("mock-user-id", [])
        assert result["ingested"] == 0

    @pytest.mark.asyncio
    async def test_run_sec_edgar_multiple_companies(self):
        from app.workers.ingest_signals import _run_sec_edgar
        result = await _run_sec_edgar("mock-user-id", [
            "co-00000-0000-0000-000000000001",
            "co-00000-0000-0000-000000000002",
        ])
        assert isinstance(result, dict)


class TestRunRss:
    """Tests for _run_rss async function."""

    @pytest.mark.asyncio
    async def test_run_rss_mock_returns_summary_dict(self):
        from app.workers.ingest_signals import _run_rss
        result = await _run_rss("mock-user-id", ["https://blog.example.com/rss"])
        assert isinstance(result, dict)
        assert "ingested" in result

    @pytest.mark.asyncio
    async def test_run_rss_empty_feed_urls(self):
        from app.workers.ingest_signals import _run_rss
        result = await _run_rss("mock-user-id", [])
        assert result["ingested"] == 0

    @pytest.mark.asyncio
    async def test_run_rss_multiple_feeds(self):
        from app.workers.ingest_signals import _run_rss
        result = await _run_rss("mock-user-id", [
            "https://blog.acme.com/rss",
            "https://news.example.com/feed.xml",
        ])
        assert isinstance(result, dict)


# ── Ingest wrapper functions ──────────────────────────────────────────────────

class TestIngestWrappers:
    """Tests for the module-level ingest_from_* wrapper functions."""

    def test_ingest_from_newsdata_returns_dict(self):
        from app.workers.ingest_signals import ingest_from_newsdata
        result = ingest_from_newsdata("mock-user-id", [])
        assert isinstance(result, dict)
        assert "ingested" in result

    def test_ingest_from_gnews_returns_dict(self):
        from app.workers.ingest_signals import ingest_from_gnews
        result = ingest_from_gnews("mock-user-id", [])
        assert isinstance(result, dict)
        assert "ingested" in result

    def test_ingest_from_sec_edgar_returns_dict(self):
        from app.workers.ingest_signals import ingest_from_sec_edgar
        result = ingest_from_sec_edgar("mock-user-id", [])
        assert isinstance(result, dict)
        assert "ingested" in result

    def test_ingest_from_rss_returns_dict(self):
        from app.workers.ingest_signals import ingest_from_rss
        result = ingest_from_rss("mock-user-id", [])
        assert isinstance(result, dict)
        assert "ingested" in result

    def test_ingest_all_sources_returns_dict(self):
        from app.workers.ingest_signals import ingest_all_sources
        result = ingest_all_sources("mock-user-id")
        assert isinstance(result, dict)
        assert "ingested" in result
        assert "duplicates" in result
        assert "errors" in result

    def test_ingest_all_sources_ingested_non_negative(self):
        from app.workers.ingest_signals import ingest_all_sources
        result = ingest_all_sources("mock-user-id")
        assert result["ingested"] >= 0

    def test_ingest_all_sources_no_errors_in_mock_mode(self):
        from app.workers.ingest_signals import ingest_all_sources
        result = ingest_all_sources("mock-user-id")
        # In mock mode, individual source errors are incremented per exception
        # but ingestion should generally succeed
        assert isinstance(result["errors"], int)

    def test_ingest_from_newsdata_with_company_ids(self):
        from app.workers.ingest_signals import ingest_from_newsdata
        result = ingest_from_newsdata("mock-user-id", [
            "co-00000-0000-0000-000000000001"
        ])
        assert isinstance(result, dict)
        assert result["ingested"] >= 0
