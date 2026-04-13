"""
Gmail integration client for Apex.

Responsibilities:
  - Build Google OAuth 2.0 authorization URL
  - Exchange authorization code for access + refresh tokens
  - Send email via Gmail API (using per-user access token)
  - Check whether sent messages have received replies (thread length > 1)

Token storage and refresh are handled by OutreachService, not this client.
This client is stateless — it receives tokens as arguments.

Gmail API scopes required:
  - https://www.googleapis.com/auth/gmail.send   (send email)
  - https://www.googleapis.com/auth/gmail.readonly (check replies)
"""

from __future__ import annotations

import base64
import email.mime.text
import logging
import urllib.parse
from typing import Any

import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailSendError(Exception):
    """Raised when Gmail API send call fails."""


class GmailOAuthError(Exception):
    """Raised when OAuth token exchange or refresh fails."""


class GmailClient:
    """
    Stateless Gmail API client.

    All methods receive the access_token as a parameter — this client does
    not store or manage tokens. Token persistence is the OutreachService's job.

    Usage:
        client = GmailClient(settings=get_settings())
        url = client.get_auth_url(user_id="user-001")
        tokens = await client.exchange_code(code="4/...")
        msg_id = await client.send_email(access_token=..., to_email=..., ...)
    """

    def __init__(self, settings: Any) -> None:
        self._client_id = settings.GMAIL_CLIENT_ID
        self._client_secret = settings.GMAIL_CLIENT_SECRET
        self._redirect_uri = settings.GMAIL_REDIRECT_URI

    # ── OAuth flow ─────────────────────────────────────────────────────────────

    def get_auth_url(self, user_id: str) -> str:
        """
        Build the Google OAuth 2.0 authorization URL.

        The user_id is embedded in the `state` parameter so the callback
        handler knows which user is completing the flow.
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": user_id,
        }
        return f"{_AUTH_BASE}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """
        Exchange an authorization code for access + refresh tokens.

        Returns dict with: access_token, refresh_token, expires_in, token_type.
        Raises GmailOAuthError if exchange fails.
        """
        payload = {
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }
        try:
            resp = requests.post(_TOKEN_URL, data=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise GmailOAuthError(f"Token exchange failed: {exc}") from exc

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Use a refresh token to obtain a new access token.

        Returns new access_token string.
        Raises GmailOAuthError if refresh fails.
        """
        payload = {
            "refresh_token": refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
        }
        try:
            resp = requests.post(_TOKEN_URL, data=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data["access_token"]
        except Exception as exc:
            raise GmailOAuthError(f"Token refresh failed: {exc}") from exc

    # ── Email send ─────────────────────────────────────────────────────────────

    async def send_email(
        self,
        access_token: str,
        to_email: str,
        subject: str,
        body: str,
    ) -> str:
        """
        Send a plain-text email via the Gmail API.

        Returns Gmail message ID of the sent message.
        Raises GmailSendError if the Gmail API call fails.
        """
        try:
            creds = Credentials(token=access_token)
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)

            mime_msg = email.mime.text.MIMEText(body, "plain")
            mime_msg["to"] = to_email
            mime_msg["subject"] = subject

            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
            result = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
            return result["id"]
        except Exception as exc:
            raise GmailSendError(f"Failed to send email to {to_email}: {exc}") from exc

    # ── Reply checking ─────────────────────────────────────────────────────────

    async def check_replies(
        self,
        access_token: str,
        message_ids: list[str],
    ) -> dict[str, bool]:
        """
        Check whether any of the given sent messages have received a reply.

        Gmail threads: if a thread has more than one message, a reply exists.
        Returns dict mapping message_id -> True (has reply) / False (no reply).
        On error, returns False for all IDs (does not raise).
        """
        if not message_ids:
            return {}

        try:
            creds = Credentials(token=access_token)
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            result: dict[str, bool] = {}

            for msg_id in message_ids:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="metadata")
                    .execute()
                )
                thread_id = msg.get("threadId", msg_id)
                thread = (
                    service.users()
                    .threads()
                    .get(userId="me", id=thread_id)
                    .execute()
                )
                messages_in_thread = thread.get("messages", [])
                result[msg_id] = len(messages_in_thread) > 1

            return result
        except Exception as exc:
            logger.warning("check_replies failed for %s: %s", message_ids, exc)
            return {msg_id: False for msg_id in message_ids}
