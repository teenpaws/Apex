"""
Integration tests for Contacts API endpoints.

Tests cover:
  GET  /api/v1/contacts          — list contacts (with optional company_id filter)
  POST /api/v1/contacts/search   — search PDL for contacts
  GET  /api/v1/contacts/{id}     — contact detail

All tests run with USE_MOCK_DATA=true. The mock data is loaded from
backend/app/api/mock_responses/contacts.json.

Auth is bypassed via the MockUser fixture injected by conftest.py.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_CONTACTS_MODULE = "app.api.v1.contacts"
_SERVICE_MODULE = "app.services.contact_service"


def _skip_if_missing():
    pytest.importorskip(_CONTACTS_MODULE)


# ===========================================================================
# GET /contacts
# ===========================================================================

class TestListContacts:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_CONTACTS_MODULE)

    @pytest.mark.asyncio
    async def test_list_contacts_returns_200(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_contacts_returns_contacts_list(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts")
        data = resp.json()
        assert "contacts" in data
        assert isinstance(data["contacts"], list)

    @pytest.mark.asyncio
    async def test_list_contacts_has_total(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts")
        data = resp.json()
        assert "total" in data
        assert isinstance(data["total"], int)
        assert data["total"] == len(data["contacts"])

    @pytest.mark.asyncio
    async def test_list_contacts_returns_at_least_one(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts")
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_contacts_filter_by_company_id(self, async_client: AsyncClient):
        """Filtering by company_id should return only contacts at that company."""
        resp = await async_client.get(
            "/api/v1/contacts",
            params={"company_id": "co-00000-0000-0000-000000000002"},
        )
        data = resp.json()
        assert resp.status_code == 200
        for contact in data["contacts"]:
            assert contact["company_id"] == "co-00000-0000-0000-000000000002"

    @pytest.mark.asyncio
    async def test_list_contacts_filter_unknown_company_returns_empty(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/api/v1/contacts",
            params={"company_id": "co-does-not-exist"},
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["contacts"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_contacts_contact_has_required_fields(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts")
        data = resp.json()
        assert len(data["contacts"]) >= 1
        contact = data["contacts"][0]
        assert "id" in contact
        assert "name" in contact
        assert "title" in contact


# ===========================================================================
# POST /contacts/search
# ===========================================================================

class TestSearchContacts:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_CONTACTS_MODULE)

    @pytest.mark.asyncio
    async def test_search_returns_200(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/contacts/search",
            json={
                "company_name": "McKinsey & Company",
                "title_keywords": ["VP Strategy", "Chief of Staff"],
                "limit": 5,
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_search_returns_contacts_list(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/contacts/search",
            json={
                "company_name": "McKinsey & Company",
                "title_keywords": ["VP Strategy"],
            },
        )
        data = resp.json()
        assert "contacts" in data
        assert isinstance(data["contacts"], list)

    @pytest.mark.asyncio
    async def test_search_returns_at_least_one_contact(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/contacts/search",
            json={
                "company_name": "McKinsey & Company",
                "title_keywords": ["VP Strategy"],
            },
        )
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_search_limit_respected(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/contacts/search",
            json={
                "company_name": "McKinsey & Company",
                "title_keywords": ["VP Strategy"],
                "limit": 1,
            },
        )
        data = resp.json()
        assert len(data["contacts"]) <= 1

    @pytest.mark.asyncio
    async def test_search_missing_company_name_returns_422(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/contacts/search",
            json={"title_keywords": ["VP Strategy"]},  # missing company_name
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_search_missing_title_keywords_returns_422(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/contacts/search",
            json={"company_name": "McKinsey"},  # missing title_keywords
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_search_contact_has_name_and_title(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/contacts/search",
            json={
                "company_name": "McKinsey & Company",
                "title_keywords": ["VP Strategy"],
            },
        )
        data = resp.json()
        if data["contacts"]:
            contact = data["contacts"][0]
            assert "name" in contact
            assert "title" in contact


# ===========================================================================
# GET /contacts/{contact_id}
# ===========================================================================

class TestGetContact:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_CONTACTS_MODULE)

    @pytest.mark.asyncio
    async def test_get_contact_returns_200(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts/ct-00000-0000-0000-000000000001")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_contact_returns_correct_contact(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts/ct-00000-0000-0000-000000000001")
        data = resp.json()
        assert data["id"] == "ct-00000-0000-0000-000000000001"
        assert data["name"] == "Jane Smith"

    @pytest.mark.asyncio
    async def test_get_contact_has_required_fields(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts/ct-00000-0000-0000-000000000001")
        data = resp.json()
        assert "id" in data
        assert "name" in data
        assert "title" in data
        assert "company_id" in data

    @pytest.mark.asyncio
    async def test_get_contact_unknown_id_returns_404(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/contacts/ct-does-not-exist")
        assert resp.status_code == 404
