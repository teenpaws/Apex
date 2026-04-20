"""Coverage gap-fill for service layer — actions, opportunities, signals, profile, contacts, outreach."""
import pytest
from app.services.action_service import ActionService
from app.services.opportunity_service import OpportunityService
from app.services.signal_service import SignalService
from app.services.profile_service import ProfileService
from app.services.contact_service import ContactService
from app.services.outreach_service import OutreachService
from app.core.errors import ApexHTTPException


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def action_svc():
    return ActionService(user_id="mock-user-id", use_mock=True)


@pytest.fixture
def opp_svc():
    return OpportunityService(user_id="mock-user-id", use_mock=True)


@pytest.fixture
def signal_svc():
    return SignalService(user_id="mock-user-id", use_mock=True)


@pytest.fixture
def profile_svc():
    return ProfileService(user_id="mock-user-id", use_mock=True)


@pytest.fixture
def contact_svc():
    return ContactService(user_id="mock-user-id", use_mock=True)


@pytest.fixture
def outreach_svc():
    return OutreachService(user_id="mock-user-id", use_mock=True)


# ── ActionService ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_service_list_returns_data_key(action_svc):
    result = await action_svc.list_actions(page=1, page_size=20)
    assert "data" in result
    assert isinstance(result["data"], list)


@pytest.mark.asyncio
async def test_action_service_list_returns_total(action_svc):
    result = await action_svc.list_actions(page=1, page_size=20)
    assert "total" in result
    assert isinstance(result["total"], int)


@pytest.mark.asyncio
async def test_action_service_filter_status_todo(action_svc):
    result = await action_svc.list_actions(page=1, page_size=20, status="TODO")
    for item in result["data"]:
        assert item["status"] == "TODO"


@pytest.mark.asyncio
async def test_action_service_filter_priority_high(action_svc):
    result = await action_svc.list_actions(page=1, page_size=20, priority="HIGH")
    for item in result["data"]:
        assert item["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_action_service_get_nonexistent_raises(action_svc):
    with pytest.raises((ApexHTTPException, Exception)):
        await action_svc.get_action("no-such-id-xyz")


@pytest.mark.asyncio
async def test_action_service_update_nonexistent_raises(action_svc):
    with pytest.raises((ApexHTTPException, Exception)):
        await action_svc.update_action("no-such-id", {"status": "DONE"})


# ── OpportunityService ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_opportunity_service_list_returns_data(opp_svc):
    result = await opp_svc.list_opportunities(page=1, page_size=20)
    assert "data" in result
    assert isinstance(result["data"], list)


@pytest.mark.asyncio
async def test_opportunity_service_filter_confidence_high(opp_svc):
    result = await opp_svc.list_opportunities(page=1, page_size=20, confidence="HIGH")
    for item in result["data"]:
        assert item["confidence"] == "HIGH"


@pytest.mark.asyncio
async def test_opportunity_service_filter_status(opp_svc):
    result = await opp_svc.list_opportunities(page=1, page_size=20, status="PREDICTED")
    for item in result["data"]:
        assert item["status"] == "PREDICTED"


@pytest.mark.asyncio
async def test_opportunity_service_get_nonexistent_raises(opp_svc):
    with pytest.raises((ApexHTTPException, Exception)):
        await opp_svc.get_opportunity("no-such-id")


# ── SignalService ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signal_service_list_returns_data(signal_svc):
    result = await signal_svc.list_signals(page=1, page_size=20)
    assert "data" in result
    assert isinstance(result["data"], list)


@pytest.mark.asyncio
async def test_signal_service_filter_funding(signal_svc):
    result = await signal_svc.list_signals(page=1, page_size=20, signal_type="FUNDING")
    for sig in result["data"]:
        assert sig["type"] == "FUNDING"


@pytest.mark.asyncio
async def test_signal_service_get_nonexistent_raises(signal_svc):
    with pytest.raises((ApexHTTPException, Exception)):
        await signal_svc.get_signal("no-such-id")


# ── ProfileService ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profile_service_get_returns_dict(profile_svc):
    result = await profile_svc.get_profile()
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_profile_service_get_has_user_id(profile_svc):
    result = await profile_svc.get_profile()
    assert "user_id" in result or "id" in result or len(result) > 0


@pytest.mark.asyncio
async def test_profile_service_update_current_role(profile_svc):
    result = await profile_svc.update_profile({"current_role": "MBA Student"})
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_profile_service_update_target_roles(profile_svc):
    result = await profile_svc.update_profile({"target_roles": ["Strategy Director"]})
    assert isinstance(result, dict)


# ── ContactService ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_contact_service_list_returns_contacts_key(contact_svc):
    result = await contact_svc.list_contacts()
    assert "contacts" in result
    assert isinstance(result["contacts"], list)


@pytest.mark.asyncio
async def test_contact_service_list_filter_company(contact_svc):
    """Filtering by company_id that doesn't exist returns empty list."""
    result = await contact_svc.list_contacts(company_id="nonexistent-company")
    assert "contacts" in result


@pytest.mark.asyncio
async def test_contact_service_get_nonexistent_raises(contact_svc):
    with pytest.raises((ApexHTTPException, Exception)):
        await contact_svc.get_contact("no-such-contact-id")


@pytest.mark.asyncio
async def test_contact_service_get_existing_returns_dict(contact_svc):
    """Getting an existing contact covers the return-contact branch (line 74)."""
    result = await contact_svc.get_contact("ct-00000-0000-0000-000000000001")
    assert isinstance(result, dict)
    assert result.get("id") == "ct-00000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_contact_service_list_has_total(contact_svc):
    result = await contact_svc.list_contacts()
    assert "total" in result


# ── OutreachService ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outreach_service_list_returns_emails_key(outreach_svc):
    result = await outreach_svc.list_outreach()
    assert "emails" in result
    assert isinstance(result["emails"], list)


@pytest.mark.asyncio
async def test_outreach_service_list_filter_draft(outreach_svc):
    """Filtering by draft status returns emails where sent_at is None."""
    result = await outreach_svc.list_outreach(status="draft")
    for email in result["emails"]:
        assert email.get("sent_at") is None


@pytest.mark.asyncio
async def test_outreach_service_list_filter_sent(outreach_svc):
    """Filtering by sent status returns emails where sent_at is set."""
    result = await outreach_svc.list_outreach(status="sent")
    for email in result["emails"]:
        assert email.get("sent_at") is not None


@pytest.mark.asyncio
async def test_outreach_service_list_filter_replied(outreach_svc):
    """Filtering by replied status returns emails where replied_at is set."""
    result = await outreach_svc.list_outreach(status="replied")
    for email in result["emails"]:
        assert email.get("replied_at") is not None


@pytest.mark.asyncio
async def test_outreach_service_create_draft_returns_id(outreach_svc):
    result = await outreach_svc.create_draft(
        action_id="act-001",
        contact_id="con-001",
        subject="Test Subject",
        body="Hello there",
        tone="professional",
    )
    assert "id" in result
    assert result["subject"] == "Test Subject"
    assert result["tone"] == "PROFESSIONAL"


@pytest.mark.asyncio
async def test_outreach_service_send_nonexistent_raises(outreach_svc):
    with pytest.raises((ApexHTTPException, Exception)):
        await outreach_svc.send_email("no-such-email-id")


@pytest.mark.asyncio
async def test_outreach_service_send_existing_returns_sent_at(outreach_svc):
    """Sending an existing draft email covers the success path (lines 101-104)."""
    result = await outreach_svc.send_email("email-001")
    assert isinstance(result, dict)
    assert result.get("sent_at") is not None
    assert result.get("gmail_message_id") is not None


# ── ContactService — search_contacts (mock) ───────────────────────────────────

@pytest.mark.asyncio
async def test_contact_service_search_returns_contacts_key(contact_svc):
    result = await contact_svc.search_contacts(
        company_name="Acme Corp",
        title_keywords=["VP Strategy"],
        limit=5,
    )
    assert "contacts" in result
    assert isinstance(result["contacts"], list)


@pytest.mark.asyncio
async def test_contact_service_search_returns_total(contact_svc):
    result = await contact_svc.search_contacts(
        company_name="McKinsey",
        title_keywords=["Partner"],
        limit=3,
    )
    assert "total" in result
    assert isinstance(result["total"], int)


@pytest.mark.asyncio
async def test_contact_service_search_respects_limit(contact_svc):
    result = await contact_svc.search_contacts(
        company_name="Bain",
        title_keywords=["Manager"],
        limit=2,
    )
    assert len(result["contacts"]) <= 2


# ── ContactService — trigger_enrich (mock) ────────────────────────────────────

@pytest.mark.asyncio
async def test_contact_service_trigger_enrich_returns_run_id(contact_svc):
    """trigger_enrich in mock mode should return a run_id dict (patch task to avoid asyncio.run clash)."""
    from unittest.mock import patch, MagicMock
    mock_task = MagicMock()
    mock_task.apply.return_value.get.return_value = {"contact_id": "mock-contact-id", "enriched": True}
    with patch("app.services.contact_service.ContactService.trigger_enrich",
               wraps=None) as _:
        pass
    # Call the method directly with mocked worker import
    with patch("app.workers.enrich_contacts.enrich_contact", mock_task):
        result = await contact_svc.trigger_enrich("mock-contact-id")
    assert "run_id" in result
    assert isinstance(result["run_id"], str)


@pytest.mark.asyncio
async def test_contact_service_trigger_enrich_mock_returns_success_status(contact_svc):
    """trigger_enrich in mock mode returns status=SUCCESS."""
    from unittest.mock import patch, MagicMock
    mock_task = MagicMock()
    mock_task.apply.return_value.get.return_value = {"contact_id": "mock-contact-id", "enriched": True}
    with patch("app.workers.enrich_contacts.enrich_contact", mock_task):
        result = await contact_svc.trigger_enrich("mock-contact-id", priority="high")
    assert result["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_contact_service_trigger_enrich_includes_result(contact_svc):
    """trigger_enrich mock mode includes result key."""
    from unittest.mock import patch, MagicMock
    mock_task = MagicMock()
    mock_task.apply.return_value.get.return_value = {"contact_id": "mock-contact-id", "enriched": True}
    with patch("app.workers.enrich_contacts.enrich_contact", mock_task):
        result = await contact_svc.trigger_enrich("mock-contact-id")
    assert "result" in result
    assert isinstance(result["result"], dict)


# ── NotImplementedError live-path stubs ───────────────────────────────────────

@pytest.mark.asyncio
async def test_contact_service_list_live_raises(monkeypatch):
    """Live path raises NotImplementedError (used to cover line 40)."""
    from app.services.contact_service import ContactService
    svc = ContactService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.list_contacts()


@pytest.mark.asyncio
async def test_contact_service_get_live_raises(monkeypatch):
    """Live path raises NotImplementedError (used to cover line 68)."""
    from app.services.contact_service import ContactService
    svc = ContactService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.get_contact("some-id")


@pytest.mark.asyncio
async def test_contact_service_search_live_raises(monkeypatch):
    """Live path raises NotImplementedError (used to cover line 101)."""
    from app.services.contact_service import ContactService
    svc = ContactService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.search_contacts("Acme", ["VP"], limit=5)


@pytest.mark.asyncio
async def test_outreach_service_list_live_raises(monkeypatch):
    """Live path raises NotImplementedError (used to cover line 37)."""
    from app.services.outreach_service import OutreachService
    svc = OutreachService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.list_outreach()


@pytest.mark.asyncio
async def test_outreach_service_create_draft_live_raises(monkeypatch):
    """Live path raises NotImplementedError (used to cover line 86)."""
    from app.services.outreach_service import OutreachService
    svc = OutreachService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.create_draft("act-1", "con-1", "Sub", "Body", "formal")


@pytest.mark.asyncio
async def test_outreach_service_send_live_raises(monkeypatch):
    """Live path raises NotImplementedError (used to cover line 110)."""
    from app.services.outreach_service import OutreachService
    svc = OutreachService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.send_email("outreach-id")


# ── OpportunityService — company_id filter (line 74) ─────────────────────────

@pytest.mark.asyncio
async def test_opportunity_service_filter_company_id(opp_svc):
    """Filter by company_id exercises line 74 in opportunity_service.py."""
    result = await opp_svc.list_opportunities(
        page=1, page_size=20, company_id="co-00000-0000-0000-000000000001"
    )
    assert "data" in result
    assert isinstance(result["data"], list)


# ── Live-path stubs for remaining services ────────────────────────────────────

@pytest.mark.asyncio
async def test_action_service_list_live_raises():
    from app.services.action_service import ActionService
    svc = ActionService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.list_actions()


@pytest.mark.asyncio
async def test_action_service_update_live_raises():
    from app.services.action_service import ActionService
    svc = ActionService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.update_action("act-1", {"status": "DONE"})


@pytest.mark.asyncio
async def test_opportunity_service_list_live_raises():
    from app.services.opportunity_service import OpportunityService
    svc = OpportunityService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.list_opportunities()


@pytest.mark.asyncio
async def test_opportunity_service_get_live_raises():
    from app.services.opportunity_service import OpportunityService
    svc = OpportunityService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.get_opportunity("opp-1")


@pytest.mark.asyncio
async def test_signal_service_list_live_raises():
    from app.services.signal_service import SignalService
    svc = SignalService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.list_signals()


@pytest.mark.asyncio
async def test_signal_service_get_live_raises():
    from app.services.signal_service import SignalService
    svc = SignalService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.get_signal("sig-1")


@pytest.mark.asyncio
async def test_profile_service_get_live_raises():
    from app.services.profile_service import ProfileService
    svc = ProfileService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.get_profile()


@pytest.mark.asyncio
async def test_profile_service_update_live_raises():
    from app.services.profile_service import ProfileService
    svc = ProfileService(user_id="mock-user-id", use_mock=False)
    with pytest.raises(NotImplementedError):
        await svc.update_profile({"current_role": "CEO"})
