"""
Unit tests for GmailClient.

Tests cover:
  - get_auth_url returns valid Google OAuth URL containing accounts.google.com
  - get_auth_url embeds user_id in state parameter
  - exchange_code returns token dict (requests.post mocked)
  - send_email returns gmail_message_id (googleapiclient.build mocked)
  - send_email raises GmailSendError on API failure
  - check_replies returns False when thread has only 1 message
  - check_replies returns True when thread has 2+ messages
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


_MODULE = "app.integrations.gmail_client"


class TestGetAuthUrl:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_returns_google_oauth_url(self):
        from app.integrations.gmail_client import GmailClient
        from app.core.config import get_settings
        client = GmailClient(settings=get_settings())
        url = client.get_auth_url(user_id="user-001")
        assert "accounts.google.com" in url
        assert "redirect_uri" in url
        assert "scope" in url

    def test_url_includes_state_with_user_id(self):
        from app.integrations.gmail_client import GmailClient
        from app.core.config import get_settings
        client = GmailClient(settings=get_settings())
        url = client.get_auth_url(user_id="user-abc")
        assert "user-abc" in url


class TestExchangeCode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_exchange_code_returns_token_dict(self):
        from app.integrations.gmail_client import GmailClient
        from app.core.config import get_settings

        mock_token = {
            "access_token": "ya29.test",
            "refresh_token": "1//test-refresh",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        with patch("app.integrations.gmail_client.requests.post") as mock_post:
            mock_post.return_value.json.return_value = mock_token
            mock_post.return_value.raise_for_status = MagicMock()

            client = GmailClient(settings=get_settings())
            result = await client.exchange_code(code="4/test-auth-code")

        assert result["access_token"] == "ya29.test"
        assert result["refresh_token"] == "1//test-refresh"


class TestSendEmail:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_send_email_returns_message_id(self):
        from app.integrations.gmail_client import GmailClient
        from app.core.config import get_settings

        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "msg-xyz789"
        }

        with patch("app.integrations.gmail_client.build", return_value=mock_service):
            client = GmailClient(settings=get_settings())
            msg_id = await client.send_email(
                access_token="ya29.test",
                to_email="sarah@stripe.com",
                subject="Test subject",
                body="Test body",
            )

        assert msg_id == "msg-xyz789"

    @pytest.mark.asyncio
    async def test_send_email_raises_on_api_error(self):
        from app.integrations.gmail_client import GmailClient, GmailSendError
        from app.core.config import get_settings

        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = Exception(
            "Gmail API error"
        )

        with patch("app.integrations.gmail_client.build", return_value=mock_service):
            client = GmailClient(settings=get_settings())
            with pytest.raises(GmailSendError):
                await client.send_email(
                    access_token="ya29.test",
                    to_email="sarah@stripe.com",
                    subject="Test",
                    body="Body",
                )


class TestCheckReplies:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_check_replies_returns_false_when_no_thread(self):
        from app.integrations.gmail_client import GmailClient
        from app.core.config import get_settings

        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
            "id": "msg-001",
            "threadId": "thread-001",
        }
        mock_service.users.return_value.threads.return_value.get.return_value.execute.return_value = {
            "messages": [{"id": "msg-001"}]
        }

        with patch("app.integrations.gmail_client.build", return_value=mock_service):
            client = GmailClient(settings=get_settings())
            result = await client.check_replies(
                access_token="ya29.test",
                message_ids=["msg-001"],
            )

        assert result == {"msg-001": False}

    @pytest.mark.asyncio
    async def test_check_replies_returns_true_when_thread_has_reply(self):
        from app.integrations.gmail_client import GmailClient
        from app.core.config import get_settings

        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
            "id": "msg-001",
            "threadId": "thread-001",
        }
        mock_service.users.return_value.threads.return_value.get.return_value.execute.return_value = {
            "messages": [{"id": "msg-001"}, {"id": "reply-002"}]
        }

        with patch("app.integrations.gmail_client.build", return_value=mock_service):
            client = GmailClient(settings=get_settings())
            result = await client.check_replies(
                access_token="ya29.test",
                message_ids=["msg-001"],
            )

        assert result == {"msg-001": True}

    @pytest.mark.asyncio
    async def test_check_replies_empty_list_returns_empty_dict(self):
        from app.integrations.gmail_client import GmailClient
        from app.core.config import get_settings
        client = GmailClient(settings=get_settings())
        result = await client.check_replies(access_token="ya29.test", message_ids=[])
        assert result == {}
