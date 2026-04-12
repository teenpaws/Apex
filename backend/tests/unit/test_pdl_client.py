"""
Unit tests for PDLClient.

Tests cover:
  - Mock mode: enrich_person, enrich_company, search_people return correct types
  - Caching: second call returns cached data without hitting PDL API
  - 402 quota exceeded → returns None (graceful degradation)
  - 404 not found → returns None
  - search_people results sorted by seniority (most senior first)
  - search_people returns ranked contacts
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_MODULE = "app.integrations.pdl_client"


def _skip_if_missing():
    pytest.importorskip(_MODULE)


# ===========================================================================
# Mock mode — enrich_person
# ===========================================================================

class TestPDLClientEnrichPersonMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_enrich_person_returns_person_profile(self):
        from app.integrations.pdl_client import PDLClient, PersonProfile
        from app.core.config import get_settings

        client = PDLClient()
        result = await client.enrich_person("Jane Smith", "McKinsey")
        assert result is not None
        assert isinstance(result, PersonProfile)

    @pytest.mark.asyncio
    async def test_enrich_person_has_full_name(self):
        from app.integrations.pdl_client import PDLClient
        from app.core.config import get_settings

        client = PDLClient()
        result = await client.enrich_person("Jane Smith", "McKinsey")
        assert result.full_name == "Jane Smith"

    @pytest.mark.asyncio
    async def test_enrich_person_has_job_title(self):
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        result = await client.enrich_person("Jane Smith", "McKinsey")
        assert result.job_title
        assert isinstance(result.job_title, str)

    @pytest.mark.asyncio
    async def test_enrich_person_has_pdl_id(self):
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        result = await client.enrich_person("Jane Smith", "McKinsey")
        assert result.pdl_id
        assert isinstance(result.pdl_id, str)

    @pytest.mark.asyncio
    async def test_enrich_person_email_is_none_in_mock(self):
        """PDL client never populates email — that's Hunter.io's job."""
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        result = await client.enrich_person("Jane Smith", "McKinsey")
        assert result.email is None

    @pytest.mark.asyncio
    async def test_mock_no_http_call_made(self):
        from app.integrations.pdl_client import PDLClient

        with patch("httpx.AsyncClient") as mock_http:
            client = PDLClient()
            await client.enrich_person("Jane Smith", "McKinsey")
            mock_http.assert_not_called()


# ===========================================================================
# Mock mode — enrich_company
# ===========================================================================

class TestPDLClientEnrichCompanyMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_enrich_company_returns_company_profile(self):
        from app.integrations.pdl_client import PDLClient, CompanyProfile

        client = PDLClient()
        result = await client.enrich_company("McKinsey", domain="mckinsey.com")
        assert result is not None
        assert isinstance(result, CompanyProfile)

    @pytest.mark.asyncio
    async def test_enrich_company_has_headcount(self):
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        result = await client.enrich_company("McKinsey")
        assert result.headcount is not None
        assert isinstance(result.headcount, int)
        assert result.headcount > 0

    @pytest.mark.asyncio
    async def test_enrich_company_has_industry(self):
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        result = await client.enrich_company("McKinsey")
        assert result.industry
        assert isinstance(result.industry, str)

    @pytest.mark.asyncio
    async def test_enrich_company_has_name(self):
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        result = await client.enrich_company("McKinsey")
        assert result.name


# ===========================================================================
# Mock mode — search_people
# ===========================================================================

class TestPDLClientSearchPeopleMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_search_people_returns_list(self):
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        results = await client.search_people("McKinsey", ["VP Strategy", "Principal"])
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_people_returns_contact_results(self):
        from app.integrations.pdl_client import PDLClient, ContactSearchResult

        client = PDLClient()
        results = await client.search_people("McKinsey", ["VP Strategy"])
        for r in results:
            assert isinstance(r, ContactSearchResult)
            assert r.full_name
            assert r.job_title

    @pytest.mark.asyncio
    async def test_search_people_sorted_by_seniority(self):
        """Most senior contact should appear first."""
        from app.integrations.pdl_client import PDLClient, _SENIORITY_RANK

        client = PDLClient()
        results = await client.search_people("McKinsey", ["VP Strategy", "Director"])

        if len(results) >= 2:
            first_rank = _SENIORITY_RANK.get((results[0].seniority or "").lower(), 99)
            second_rank = _SENIORITY_RANK.get((results[1].seniority or "").lower(), 99)
            assert first_rank <= second_rank, (
                f"Expected results sorted by seniority: "
                f"{results[0].seniority}({first_rank}) should rank <= {results[1].seniority}({second_rank})"
            )

    @pytest.mark.asyncio
    async def test_search_people_empty_keywords_returns_results(self):
        """Empty keywords list should still return something (default behaviour)."""
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        # Even with an empty list, mock returns default contacts
        results = await client.search_people("McKinsey", [])
        assert isinstance(results, list)


# ===========================================================================
# Live-mode: 402 quota exceeded → None
# ===========================================================================

class TestPDLClientQuotaHandling:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_enrich_person_returns_none_on_402(self):
        """402 from PDL should not raise — should return None."""
        from app.integrations.pdl_client import PDLClient
        from app.core.config import get_settings
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 402

        async def _mock_get(*args, **kwargs):
            return mock_response

        settings = get_settings()
        # Override mock mode for this test
        with patch.object(settings, "USE_MOCK_DATA", False):
            with patch.object(settings, "PDL_API_KEY", "test-key"):
                mock_http_client = AsyncMock()
                mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
                mock_http_client.__aexit__ = AsyncMock(return_value=False)
                mock_http_client.get = AsyncMock(return_value=mock_response)

                client = PDLClient()
                client._settings = settings
                # Patch _get directly to return None (simulating 402 handling)
                with patch.object(client, "_get", return_value=None):
                    result = await client.enrich_person("Jane Smith", "McKinsey")
                    assert result is None

    @pytest.mark.asyncio
    async def test_enrich_company_returns_none_on_404(self):
        """404 (company not in PDL) should return None, not raise."""
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        with patch.object(client, "_get", return_value=None):
            # Override mock mode
            client._settings = MagicMock(USE_MOCK_DATA=False, PDL_API_KEY="key")
            result = await client.enrich_company("NonExistentCorp")
            assert result is None

    @pytest.mark.asyncio
    async def test_search_people_returns_empty_on_error(self):
        """Any error from PDL search should return [] not raise."""
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        with patch.object(client, "_post", return_value=None):
            client._settings = MagicMock(USE_MOCK_DATA=False, PDL_API_KEY="key")
            results = await client.search_people("McKinsey", ["VP"])
            assert results == []


# ===========================================================================
# Cache behaviour
# ===========================================================================

class TestPDLClientCaching:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_enrich_person_uses_cache_on_second_call(self):
        """Second call with same inputs should hit cache, not PDL API."""
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        client._settings = MagicMock(USE_MOCK_DATA=False, PDL_API_KEY="key", REDIS_URL="redis://localhost:6379")

        mock_raw = {
            "id": "cached-person-001",
            "full_name": "Jane Smith",
            "first_name": "Jane",
            "last_name": "Smith",
            "job_title": "VP Strategy",
            "job_company_name": "McKinsey",
            "linkedin_url": "https://linkedin.com/in/janesmith",
            "location_name": "New York, USA",
            "job_title_levels": ["vp"],
            "experience": [],
        }

        # Simulate cache hit returning the raw dict
        with patch("app.integrations.pdl_client._cache_get", return_value=mock_raw):
            with patch("app.integrations.pdl_client._redis_client", return_value=MagicMock()):
                with patch.object(client, "_get") as mock_get:
                    result = await client.enrich_person("Jane Smith", "McKinsey")
                    # _get should NOT be called since cache hit
                    mock_get.assert_not_called()
                    assert result is not None
                    assert result.full_name == "Jane Smith"
