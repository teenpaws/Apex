"""
Integration tests for the Outreach API routes.

Tests cover:
  - GET /outreach — returns mock email list
  - GET /outreach?status=draft — filters to drafts only
  - POST /outreach/draft — generates email draft via EmailDrafterAgent (mock mode)
  - POST /outreach/draft missing action_id — returns 422
  - POST /outreach/{id}/send — marks email as sent (mock mode)
  - POST /outreach/does-not-exist/send — returns 404
  - POST /outreach/oauth/connect — returns redirect_url to Google
  - GET /outreach/oauth/callback — returns connected message in mock mode

All tests run with USE_MOCK_DATA=True so no real DB or Gmail calls are made.
"""

from __future__ import annotations

import pytest


BASE = "/api/v1/outreach"


class TestListOutreach:

    @pytest.mark.asyncio
    async def test_list_returns_emails(self, async_client):
        response = await async_client.get(BASE)
        assert response.status_code == 200
        data = response.json()
        assert "emails" in data
        assert isinstance(data["emails"], list)

    @pytest.mark.asyncio
    async def test_list_filters_by_status_draft(self, async_client):
        response = await async_client.get(BASE, params={"status": "draft"})
        assert response.status_code == 200
        data = response.json()
        for email in data["emails"]:
            assert email["sent_at"] is None


class TestCreateDraft:

    @pytest.mark.asyncio
    async def test_draft_returns_email_record(self, async_client):
        payload = {
            "action_id": "action-001",
            "contact_id": "contact-001",
        }
        response = await async_client.post(f"{BASE}/draft", json=payload)
        assert response.status_code == 200
        data = response.json()
        # Mock mode returns the draft record directly
        assert "id" in data or "run_id" in data

    @pytest.mark.asyncio
    async def test_draft_missing_action_id_returns_422(self, async_client):
        response = await async_client.post(f"{BASE}/draft", json={"contact_id": "contact-001"})
        assert response.status_code == 422


class TestSendEmail:

    @pytest.mark.asyncio
    async def test_send_existing_draft_returns_200(self, async_client):
        response = await async_client.post(f"{BASE}/email-001/send")
        assert response.status_code == 200
        data = response.json()
        assert data.get("sent_at") is not None or data.get("gmail_message_id") is not None

    @pytest.mark.asyncio
    async def test_send_nonexistent_id_returns_404(self, async_client):
        response = await async_client.post(f"{BASE}/does-not-exist/send")
        assert response.status_code == 404


class TestGmailOAuth:

    @pytest.mark.asyncio
    async def test_oauth_connect_returns_redirect_url(self, async_client):
        response = await async_client.post(f"{BASE}/oauth/connect")
        assert response.status_code == 200
        data = response.json()
        assert "redirect_url" in data
        assert "accounts.google.com" in data["redirect_url"]

    @pytest.mark.asyncio
    async def test_oauth_callback_returns_connected_in_mock_mode(self, async_client):
        response = await async_client.get(
            f"{BASE}/oauth/callback",
            params={"code": "4/test-code", "state": "mock-user-id"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
