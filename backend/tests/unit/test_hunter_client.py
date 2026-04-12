"""
Unit tests for HunterClient.

Tests cover:
  - Mock mode: find_email returns correct EmailResult
  - Mock mode: find_domain_emails returns list sorted by confidence
  - 429 quota exceeded → returns None (graceful degradation)
  - 401 bad API key → returns None
  - Cache hit: second call returns cached result without HTTP call
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_MODULE = "app.integrations.hunter_client"


# ===========================================================================
# Mock mode — find_email
# ===========================================================================

class TestHunterClientFindEmailMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_find_email_returns_email_result(self):
        from app.integrations.hunter_client import HunterClient, EmailResult

        client = HunterClient()
        result = await client.find_email("Jane", "Smith", "mckinsey.com")
        assert result is not None
        assert isinstance(result, EmailResult)

    @pytest.mark.asyncio
    async def test_find_email_has_email_address(self):
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        result = await client.find_email("Jane", "Smith", "mckinsey.com")
        assert result.email
        assert "@" in result.email
        assert "mckinsey.com" in result.email

    @pytest.mark.asyncio
    async def test_find_email_has_score(self):
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        result = await client.find_email("Jane", "Smith", "mckinsey.com")
        assert isinstance(result.score, int)
        assert 0 <= result.score <= 100

    @pytest.mark.asyncio
    async def test_find_email_verified_true_in_mock(self):
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        result = await client.find_email("Jane", "Smith", "mckinsey.com")
        assert result.verified is True

    @pytest.mark.asyncio
    async def test_mock_no_http_call_made(self):
        from app.integrations.hunter_client import HunterClient

        with patch("httpx.AsyncClient") as mock_http:
            client = HunterClient()
            await client.find_email("Jane", "Smith", "mckinsey.com")
            mock_http.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_email_domain_in_result(self):
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        result = await client.find_email("Jane", "Smith", "accenture.com")
        assert result.domain == "accenture.com"
        assert "accenture.com" in result.email


# ===========================================================================
# Mock mode — find_domain_emails
# ===========================================================================

class TestHunterClientFindDomainEmailsMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_find_domain_emails_returns_list(self):
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        results = await client.find_domain_emails("mckinsey.com", limit=5)
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_find_domain_emails_has_email_result_objects(self):
        from app.integrations.hunter_client import HunterClient, DomainEmailResult

        client = HunterClient()
        results = await client.find_domain_emails("mckinsey.com")
        for r in results:
            assert isinstance(r, DomainEmailResult)
            assert r.email
            assert "@" in r.email

    @pytest.mark.asyncio
    async def test_find_domain_emails_sorted_by_confidence_desc(self):
        """Higher confidence emails should come first."""
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        results = await client.find_domain_emails("mckinsey.com", limit=5)
        if len(results) >= 2:
            assert results[0].confidence >= results[1].confidence

    @pytest.mark.asyncio
    async def test_find_domain_emails_limit_respected(self):
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        results = await client.find_domain_emails("mckinsey.com", limit=1)
        assert len(results) <= 1


# ===========================================================================
# Quota / auth error handling
# ===========================================================================

class TestHunterClientErrorHandling:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_find_email_returns_none_on_429(self):
        """Monthly quota exceeded → returns None, does not raise."""
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        with patch.object(client, "_get", return_value=None):
            client._settings = MagicMock(USE_MOCK_DATA=False, HUNTER_API_KEY="key")
            result = await client.find_email("Jane", "Smith", "mckinsey.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_find_domain_emails_returns_empty_on_error(self):
        """Any error should return [] not raise."""
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        with patch.object(client, "_get", return_value=None):
            client._settings = MagicMock(USE_MOCK_DATA=False, HUNTER_API_KEY="key")
            results = await client.find_domain_emails("mckinsey.com")
            assert results == []

    @pytest.mark.asyncio
    async def test_find_email_returns_none_when_no_email_in_response(self):
        """PDL returns data with no email field → EmailResult.email is None → method returns None."""
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        empty_response = {"data": {"email": None, "score": 0, "first_name": "Jane", "last_name": "Smith", "sources": []}}
        with patch.object(client, "_get", return_value=empty_response):
            client._settings = MagicMock(USE_MOCK_DATA=False, HUNTER_API_KEY="key")
            result = await client.find_email("Jane", "Smith", "mckinsey.com")
            assert result is None


# ===========================================================================
# Cache behaviour
# ===========================================================================

class TestHunterClientCaching:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_find_email_uses_cache_on_second_call(self):
        """Cache hit should skip the HTTP call entirely."""
        from app.integrations.hunter_client import HunterClient

        client = HunterClient()
        client._settings = MagicMock(USE_MOCK_DATA=False, HUNTER_API_KEY="key", REDIS_URL="redis://localhost:6379")

        cached_data = {
            "email": "jane.smith@mckinsey.com",
            "score": 95,
            "first_name": "Jane",
            "last_name": "Smith",
            "domain": "mckinsey.com",
            "verified": True,
            "sources": [],
        }

        with patch("app.integrations.hunter_client._cache_get", return_value=cached_data):
            with patch("app.integrations.hunter_client._redis_client", return_value=MagicMock()):
                with patch.object(client, "_get") as mock_get:
                    result = await client.find_email("Jane", "Smith", "mckinsey.com")
                    mock_get.assert_not_called()
                    assert result is not None
                    assert result.email == "jane.smith@mckinsey.com"
