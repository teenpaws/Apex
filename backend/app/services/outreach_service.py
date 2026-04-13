"""
Outreach service — business logic for email drafts, sends, and Gmail OAuth.

In mock mode (USE_MOCK_DATA=True) all operations are served from
backend/app/api/mock_responses/outreach.json.

Live mode stubs raise NotImplementedError until the Supabase DB layer
is wired in Phase 9.
"""

from __future__ import annotations

import copy
from uuid import uuid4

from app.core.errors import ApexHTTPException
from app.services._mock_loader import load_mock


class OutreachService:
    """Service layer for outreach email operations, scoped to a single user."""

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_outreach(self, status: str | None = None) -> dict:
        """
        Return all outreach emails for this user, optionally filtered by status.

        Status values: 'draft' (sent_at is null), 'sent', 'replied'
        """
        if self.use_mock:
            return self._mock_list(status=status)
        raise NotImplementedError("Live DB not yet wired")

    def _mock_list(self, status: str | None) -> dict:
        data = load_mock("outreach.json")
        items: list[dict] = data["emails"]
        items = [e for e in items if e.get("user_id") == self.user_id]

        if status == "draft":
            items = [e for e in items if e.get("sent_at") is None]
        elif status == "sent":
            items = [e for e in items if e.get("sent_at") is not None and e.get("replied_at") is None]
        elif status == "replied":
            items = [e for e in items if e.get("replied_at") is not None]

        return {"emails": items, "total": len(items)}

    # ── Draft ─────────────────────────────────────────────────────────────────

    async def create_draft(
        self,
        action_id: str,
        contact_id: str,
        subject: str,
        body: str,
        tone: str,
        draft_json: dict | None = None,
    ) -> dict:
        """
        Persist a new email draft and return the created record.

        In mock mode, returns a synthetic record with a generated UUID.
        """
        if self.use_mock:
            return {
                "id": str(uuid4()),
                "user_id": self.user_id,
                "action_id": action_id,
                "contact_id": contact_id,
                "subject": subject,
                "body": body,
                "tone": tone.upper(),
                "draft_json": draft_json,
                "sent_at": None,
                "gmail_message_id": None,
                "opened_at": None,
                "replied_at": None,
                "reply_detected_at": None,
                "created_at": "2026-04-13T10:00:00Z",
            }
        raise NotImplementedError("Live DB not yet wired")

    # ── Send ──────────────────────────────────────────────────────────────────

    async def send_email(self, outreach_id: str) -> dict:
        """
        Mark an email draft as sent and return the updated record.

        In mock mode, stamps sent_at with a fixed timestamp and adds a fake gmail_message_id.
        Live mode: calls GmailClient.send_email() + updates DB.
        """
        if self.use_mock:
            data = load_mock("outreach.json")
            for email in data["emails"]:
                if email["id"] == outreach_id and email.get("user_id") == self.user_id:
                    updated = copy.deepcopy(email)
                    updated["sent_at"] = "2026-04-13T12:00:00Z"
                    updated["gmail_message_id"] = f"msg-{uuid4().hex[:8]}"
                    return updated
            raise ApexHTTPException(
                status_code=404,
                error="Outreach email not found",
                code="OUTREACH_NOT_FOUND",
            )
        raise NotImplementedError("Live DB not yet wired")

    # ── Gmail OAuth ───────────────────────────────────────────────────────────

    async def get_gmail_auth_url(self, settings: object) -> str:
        """
        Build and return the Gmail OAuth authorization URL.

        Args:
            settings: App settings (contains GMAIL_CLIENT_ID etc.)

        Returns:
            Full Google OAuth redirect URL.
        """
        from app.integrations.gmail_client import GmailClient
        client = GmailClient(settings=settings)
        return client.get_auth_url(user_id=self.user_id)

    async def complete_gmail_oauth(
        self, code: str, settings: object
    ) -> dict:
        """
        Complete the Gmail OAuth flow: exchange code for tokens.

        In a live system, tokens would be stored encrypted in Supabase.
        For Phase 8, returns the token dict for the frontend to handle.

        Args:
            code:     Authorization code from the OAuth callback.
            settings: App settings.

        Returns:
            Token dict with access_token, refresh_token, expires_in.
        """
        from app.integrations.gmail_client import GmailClient
        client = GmailClient(settings=settings)
        tokens = await client.exchange_code(code=code)
        # TODO (Phase 9): Store tokens in Supabase user preferences
        return tokens
