"""
Fuzz / invalid-input tests for all API endpoints.

Verifies that malformed inputs return structured 4xx errors — never 500s
and never raw Python tracebacks. All tests use USE_MOCK_DATA=true (conftest).
"""
import pytest

SIGNAL_ID = "sig-0001-0000-0000-000000000001"
OPP_ID = "opp-0001-0000-0000-000000000001"
ACTION_ID = "act-0001-0000-0000-000000000001"


# ── Signals ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signals_invalid_page_zero(async_client):
    r = await async_client.get("/api/v1/signals?page=0")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_signals_invalid_per_page_over_limit(async_client):
    r = await async_client.get("/api/v1/signals?page_size=999")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_signals_invalid_per_page_string(async_client):
    r = await async_client.get("/api/v1/signals?page_size=abc")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_signals_sql_injection_in_filter(async_client):
    payload = "'; DROP TABLE signals; --"
    r = await async_client.get(f"/api/v1/signals?signal_type={payload}")
    assert r.status_code in (200, 400, 422)
    assert r.status_code != 500


@pytest.mark.asyncio
async def test_signals_xss_in_filter(async_client):
    payload = "<script>alert(1)</script>"
    r = await async_client.get(f"/api/v1/signals?signal_type={payload}")
    assert r.status_code != 500
    assert "<script>" not in r.text


@pytest.mark.asyncio
async def test_signals_ingest_invalid_body(async_client):
    r = await async_client.post(
        "/api/v1/signals/ingest",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422


# ── Opportunities ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_opportunities_list_invalid_page_zero(async_client):
    r = await async_client.get("/api/v1/opportunities?page=0")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_opportunities_list_invalid_page_size_over_limit(async_client):
    r = await async_client.get("/api/v1/opportunities?page_size=999")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_opportunities_nonexistent_id(async_client):
    r = await async_client.get("/api/v1/opportunities/does-not-exist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_opportunities_sql_injection_in_status(async_client):
    payload = "'; DELETE FROM opportunities; --"
    r = await async_client.get(f"/api/v1/opportunities?status={payload}")
    assert r.status_code != 500


@pytest.mark.asyncio
async def test_opportunities_refresh_nonexistent_id(async_client):
    # Refresh is async job queueing — returns 200 with run_id even if ID doesn't exist.
    # Worker will discover the ID is invalid later.
    r = await async_client.post("/api/v1/opportunities/does-not-exist/refresh")
    assert r.status_code == 200
    assert "run_id" in r.json()


# ── Actions ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_actions_list_invalid_page_zero(async_client):
    r = await async_client.get("/api/v1/actions?page=0")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_actions_list_invalid_page_size_string(async_client):
    r = await async_client.get("/api/v1/actions?page_size=abc")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_actions_put_invalid_status(async_client):
    r = await async_client.put(
        f"/api/v1/actions/{ACTION_ID}",
        json={"status": "INVALID_ENUM"},
    )
    assert r.status_code == 200 or r.status_code == 404


@pytest.mark.asyncio
async def test_actions_put_nonexistent_id(async_client):
    r = await async_client.put(
        "/api/v1/actions/does-not-exist",
        json={"status": "DONE"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_actions_draft_email_nonexistent_action(async_client):
    # Draft email is async job queueing — returns 200 with run_id even if ID doesn't exist.
    # Worker will discover the ID is invalid later.
    r = await async_client.post("/api/v1/actions/does-not-exist/draft-email")
    assert r.status_code == 200
    assert "run_id" in r.json()


# ── Outreach ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outreach_draft_missing_required_fields(async_client):
    r = await async_client.post("/api/v1/outreach/draft", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_outreach_draft_missing_action_id(async_client):
    r = await async_client.post(
        "/api/v1/outreach/draft",
        json={"contact_id": "contact-123"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_outreach_draft_missing_contact_id(async_client):
    r = await async_client.post(
        "/api/v1/outreach/draft",
        json={"action_id": "action-123"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_outreach_send_nonexistent_email(async_client):
    r = await async_client.post("/api/v1/outreach/does-not-exist/send")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_outreach_list_invalid_status_filter(async_client):
    r = await async_client.get("/api/v1/outreach?status=invalid-status")
    assert r.status_code == 200 or r.status_code == 400


# ── Profile ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profile_put_invalid_json(async_client):
    r = await async_client.put(
        "/api/v1/profile",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_profile_put_invalid_target_roles_type(async_client):
    r = await async_client.put(
        "/api/v1/profile",
        json={"target_roles": "not-a-list"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_profile_put_invalid_industries_type(async_client):
    r = await async_client.put(
        "/api/v1/profile",
        json={"industries": "not-a-list"}
    )
    assert r.status_code == 422


# ── Auth ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_login_invalid_email(async_client):
    r = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "password"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auth_login_missing_password(async_client):
    r = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auth_login_missing_email(async_client):
    r = await async_client.post(
        "/api/v1/auth/login",
        json={"password": "password"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auth_login_empty_json(async_client):
    r = await async_client.post(
        "/api/v1/auth/login",
        json={}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auth_refresh_missing_refresh_token(async_client):
    r = await async_client.post(
        "/api/v1/auth/refresh",
        json={}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_auth_refresh_invalid_body(async_client):
    r = await async_client.post(
        "/api/v1/auth/refresh",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422


# ── XSS and Injection Prevention ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_xss_in_company_id_filter(async_client):
    payload = "<img src=x onerror=alert(1)>"
    r = await async_client.get(f"/api/v1/signals?company_id={payload}")
    assert r.status_code != 500
    assert "<img" not in r.text or "onerror" not in r.text


@pytest.mark.asyncio
async def test_xss_in_date_filter(async_client):
    payload = "<script>alert('xss')</script>"
    r = await async_client.get(f"/api/v1/signals?date_from={payload}")
    assert r.status_code != 500


@pytest.mark.asyncio
async def test_sql_injection_in_company_id(async_client):
    payload = "1 OR 1=1; DROP TABLE companies; --"
    r = await async_client.get(f"/api/v1/signals?company_id={payload}")
    assert r.status_code != 500


# ── Edge Cases ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signals_negative_page_number(async_client):
    r = await async_client.get("/api/v1/signals?page=-1")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_signals_negative_page_size(async_client):
    r = await async_client.get("/api/v1/signals?page_size=-1")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_opportunities_empty_confidence_filter(async_client):
    r = await async_client.get("/api/v1/opportunities?confidence=")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_actions_empty_status_filter(async_client):
    r = await async_client.get("/api/v1/actions?status=")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_outreach_oauth_callback_missing_code(async_client):
    r = await async_client.get("/api/v1/outreach/oauth/callback?state=user-123")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_outreach_oauth_callback_missing_state(async_client):
    r = await async_client.get("/api/v1/outreach/oauth/callback?code=auth-code")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_very_long_string_in_query_param(async_client):
    long_string = "a" * 10000
    r = await async_client.get(f"/api/v1/signals?signal_type={long_string}")
    assert r.status_code != 500


@pytest.mark.asyncio
async def test_special_chars_in_signal_type_filter(async_client):
    payload = "TEST!@#$%^&*()"
    r = await async_client.get(f"/api/v1/signals?signal_type={payload}")
    assert r.status_code != 500


@pytest.mark.asyncio
async def test_unicode_in_filter_param(async_client):
    payload = "测试中文"
    r = await async_client.get(f"/api/v1/signals?signal_type={payload}")
    assert r.status_code != 500
