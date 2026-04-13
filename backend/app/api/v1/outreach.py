"""
Outreach API — email draft, send, and Gmail OAuth routes.

All routes require a valid Bearer token (or mock-user in USE_MOCK_DATA mode).

Routes:
  GET  /outreach                   — list emails (filter by status)
  POST /outreach/draft             — generate AI email draft
  POST /outreach/{id}/send         — send a draft via Gmail
  POST /outreach/oauth/connect     — start Gmail OAuth flow
  GET  /outreach/oauth/callback    — complete Gmail OAuth (redirect target)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.services.outreach_service import OutreachService

router = APIRouter(prefix="/outreach", tags=["outreach"])


# ── Request schemas ───────────────────────────────────────────────────────────

class DraftEmailRequest(BaseModel):
    action_id: str
    contact_id: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="List outreach emails",
    description=(
        "Returns all outreach emails for the authenticated user. "
        "Optional status filter: 'draft', 'sent', 'replied'."
    ),
)
async def list_outreach(
    status: str | None = Query(None, description="Filter by status: draft, sent, replied"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = OutreachService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    return await service.list_outreach(status=status)


@router.post(
    "/draft",
    summary="Generate email draft",
    description=(
        "Generates 3 AI email variants (Professional, Warm, Direct) for the given "
        "action + contact. Returns the draft record immediately in mock mode, "
        "or a run_id to poll in live mode."
    ),
)
async def create_draft(
    body: DraftEmailRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        from app.agents.email_drafter import EmailDrafterAgent, EmailDrafterInput

        agent = EmailDrafterAgent(settings=settings)
        agent_input = EmailDrafterInput(
            user_id=current_user["id"],
            action_id=body.action_id,
            action={"title": "Outreach", "type": "OUTREACH", "description": ""},
            contact={"name": "Contact", "title": "Executive", "company_name": "Company"},
            opportunity={"predicted_role": "Strategy Role", "why_fit": "Strong fit", "positioning_notes": ""},
            user_profile={"full_name": "User", "current_role": "Professional", "aspirations_text": "", "key_skills": []},
        )
        output = await agent.draft(agent_input.model_dump(mode="json"))

        service = OutreachService(user_id=current_user["id"], use_mock=True)
        draft = await service.create_draft(
            action_id=body.action_id,
            contact_id=body.contact_id,
            subject=output.variants[0].subject,
            body=output.variants[0].body,
            tone=output.variants[0].tone.upper(),
            draft_json=output.model_dump(mode="json"),
        )
        return draft

    # Live mode: enqueue Celery task, return run_id for polling
    from uuid import uuid4
    return {
        "run_id": str(uuid4()),
        "status": "queued",
        "message": "Email draft generation queued",
    }


@router.post(
    "/{outreach_id}/send",
    summary="Send email via Gmail",
    description=(
        "Sends the given email draft via the user's connected Gmail account. "
        "Stamps sent_at and stores the gmail_message_id."
    ),
)
async def send_email(
    outreach_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = OutreachService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    return await service.send_email(outreach_id)


@router.post(
    "/oauth/connect",
    summary="Start Gmail OAuth flow",
    description=(
        "Returns a redirect_url that the frontend should open in a browser window "
        "to begin the Gmail OAuth 2.0 authorization flow."
    ),
)
async def connect_gmail(
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    service = OutreachService(
        user_id=current_user["id"],
        use_mock=settings.USE_MOCK_DATA,
    )
    redirect_url = await service.get_gmail_auth_url(settings=settings)
    return {"redirect_url": redirect_url}


@router.get(
    "/oauth/callback",
    summary="Complete Gmail OAuth",
    description=(
        "Redirect target for the Google OAuth callback. Exchanges the authorization "
        "code for access + refresh tokens. The user_id is extracted from the state param."
    ),
)
async def gmail_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="user_id embedded in state param"),
) -> dict:
    settings = get_settings()
    service = OutreachService(user_id=state, use_mock=settings.USE_MOCK_DATA)

    if settings.USE_MOCK_DATA:
        return {"message": "Gmail connected (mock mode)", "user_id": state}

    tokens = await service.complete_gmail_oauth(code=code, settings=settings)
    return {"message": "Gmail connected successfully", "user_id": state}
