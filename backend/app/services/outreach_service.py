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
        return await self._live_list(status=status)

    async def _live_list(self, status: str | None) -> dict:
        import asyncpg
        import uuid as _uuid
        from app.db.session import get_asyncpg_db_url

        conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
        try:
            conditions = ["user_id = $1"]
            args: list = [_uuid.UUID(self.user_id)]
            if status == "draft":
                conditions.append("sent_at IS NULL")
            elif status == "sent":
                conditions.append("sent_at IS NOT NULL AND replied_at IS NULL")
            elif status == "replied":
                conditions.append("replied_at IS NOT NULL")

            where = " AND ".join(conditions)
            rows = await conn.fetch(
                f"""SELECT id, user_id, action_id, contact_id, subject, body, tone,
                           draft_json, channel, sent_at, gmail_message_id,
                           opened_at, replied_at, reply_detected_at, created_at
                    FROM outreach_emails
                    WHERE {where}
                    ORDER BY created_at DESC""",
                *args,
            )
            items = [
                {
                    "id": str(r["id"]),
                    "user_id": str(r["user_id"]),
                    "action_id": str(r["action_id"]) if r["action_id"] else None,
                    "contact_id": str(r["contact_id"]) if r["contact_id"] else None,
                    "subject": r["subject"],
                    "body": r["body"],
                    "tone": r["tone"],
                    "draft_json": r["draft_json"] or {},
                    "channel": r["channel"] or "EMAIL",
                    "sent_at": r["sent_at"].isoformat() if r["sent_at"] else None,
                    "gmail_message_id": r["gmail_message_id"],
                    "opened_at": r["opened_at"].isoformat() if r["opened_at"] else None,
                    "replied_at": r["replied_at"].isoformat() if r["replied_at"] else None,
                    "reply_detected_at": r["reply_detected_at"].isoformat() if r["reply_detected_at"] else None,
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]
            return {"emails": items, "total": len(items)}
        finally:
            await conn.close()

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
                "channel": "EMAIL",
                "sent_at": None,
                "gmail_message_id": None,
                "opened_at": None,
                "replied_at": None,
                "reply_detected_at": None,
                "created_at": "2026-04-13T10:00:00Z",
            }
        return await self._live_create_draft(action_id, contact_id, subject, body, tone, draft_json)

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
        return await self._live_send_email(outreach_id)

    async def _live_create_draft(
        self,
        action_id: str,
        contact_id: str,
        subject: str,
        body: str,
        tone: str,
        draft_json: dict | None,
    ) -> dict:
        import asyncpg
        import uuid as _uuid
        from app.db.session import get_asyncpg_db_url

        doc_id = _uuid.uuid4()
        conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
        try:
            await conn.execute(
                """INSERT INTO outreach_emails
                   (id, user_id, action_id, contact_id, subject, body, tone, draft_json, channel)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'EMAIL')""",
                doc_id,
                _uuid.UUID(self.user_id),
                _uuid.UUID(action_id) if action_id else None,
                _uuid.UUID(contact_id) if contact_id else None,
                subject,
                body,
                tone.upper(),
                draft_json or {},
            )
        finally:
            await conn.close()

        return {
            "id": str(doc_id),
            "user_id": self.user_id,
            "action_id": action_id,
            "contact_id": contact_id,
            "subject": subject,
            "body": body,
            "tone": tone.upper(),
            "draft_json": draft_json or {},
            "channel": "EMAIL",
            "sent_at": None,
            "gmail_message_id": None,
            "opened_at": None,
            "replied_at": None,
            "reply_detected_at": None,
        }

    async def _live_send_email(self, outreach_id: str) -> dict:
        import asyncpg
        import uuid as _uuid
        from datetime import datetime, timezone
        from app.db.session import get_asyncpg_db_url
        from app.integrations.gmail_client import GmailClient
        from app.core.config import get_settings

        settings = get_settings()
        conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT * FROM outreach_emails WHERE id = $1 AND user_id = $2",
                _uuid.UUID(outreach_id),
                _uuid.UUID(self.user_id),
            )
            if not row:
                raise ApexHTTPException(404, "Outreach email not found", code="OUTREACH_NOT_FOUND")

            client = GmailClient(settings=settings)
            msg_id = await client.send_email(
                user_id=self.user_id,
                to_email=row["contact_email"] if "contact_email" in row.keys() else "",
                subject=row["subject"] or "",
                body=row["body"] or "",
            )

            sent_at = datetime.now(timezone.utc)
            await conn.execute(
                "UPDATE outreach_emails SET sent_at = $1, gmail_message_id = $2 WHERE id = $3",
                sent_at,
                msg_id,
                _uuid.UUID(outreach_id),
            )
            return {
                "id": outreach_id,
                "sent_at": sent_at.isoformat(),
                "gmail_message_id": msg_id,
            }
        finally:
            await conn.close()

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
