"""
Integration tests for all Sprint 2.2 API endpoints.

Runs against the FastAPI app with USE_MOCK_DATA=true (set in conftest.py).
Tests only through the HTTP client — no direct service imports.
"""

import pytest

# ── Mock IDs taken directly from mock_responses/*.json ──────────────────────
SIGNAL_ID = "sig-0001-0000-0000-000000000001"
COMPANY_ID = "co-00000-0000-0000-000000000001"
OPP_ID = "opp-0001-0000-0000-000000000001"
ACTION_ID = "act-0001-0000-0000-000000000001"


# ═══════════════════════════════════════════════════════════════════════════════
# Signals
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_signals_returns_200(async_client):
    response = await async_client.get("/api/v1/signals")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_signals_response_shape(async_client):
    response = await async_client.get("/api/v1/signals")
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data


@pytest.mark.asyncio
async def test_list_signals_signals_is_list(async_client):
    response = await async_client.get("/api/v1/signals")
    data = response.json()
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_list_signals_filter_by_type_funding(async_client):
    response = await async_client.get("/api/v1/signals?signal_type=FUNDING")
    assert response.status_code == 200
    data = response.json()
    for signal in data["data"]:
        assert signal["type"] == "FUNDING"


@pytest.mark.asyncio
async def test_list_signals_filter_nonexistent_type_returns_empty(async_client):
    response = await async_client.get("/api/v1/signals?signal_type=NONEXISTENT")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []


@pytest.mark.asyncio
async def test_get_signal_by_valid_id(async_client):
    response = await async_client.get(f"/api/v1/signals/{SIGNAL_ID}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_signal_valid_id_returns_correct_signal(async_client):
    response = await async_client.get(f"/api/v1/signals/{SIGNAL_ID}")
    data = response.json()
    assert data["id"] == SIGNAL_ID


@pytest.mark.asyncio
async def test_get_signal_nonexistent_id_returns_404(async_client):
    response = await async_client.get("/api/v1/signals/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_signal_nonexistent_id_has_error_field(async_client):
    response = await async_client.get("/api/v1/signals/nonexistent-id")
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_trigger_ingest_returns_200(async_client):
    response = await async_client.post("/api/v1/signals/ingest", json={})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_trigger_ingest_has_run_id(async_client):
    response = await async_client.post("/api/v1/signals/ingest", json={})
    data = response.json()
    assert "run_id" in data


@pytest.mark.asyncio
async def test_trigger_ingest_status_queued(async_client):
    response = await async_client.post("/api/v1/signals/ingest", json={})
    data = response.json()
    assert data["status"] == "queued"


# ═══════════════════════════════════════════════════════════════════════════════
# Companies
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_company_by_valid_id(async_client):
    response = await async_client.get(f"/api/v1/companies/{COMPANY_ID}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_company_has_signals_key(async_client):
    response = await async_client.get(f"/api/v1/companies/{COMPANY_ID}")
    data = response.json()
    assert "signals" in data


@pytest.mark.asyncio
async def test_get_company_nonexistent_id_returns_404(async_client):
    response = await async_client.get("/api/v1/companies/nonexistent-id")
    assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Opportunities
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_opportunities_returns_200(async_client):
    response = await async_client.get("/api/v1/opportunities")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_opportunities_response_shape(async_client):
    response = await async_client.get("/api/v1/opportunities")
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data


@pytest.mark.asyncio
async def test_list_opportunities_filter_by_confidence_high(async_client):
    response = await async_client.get("/api/v1/opportunities?confidence=HIGH")
    assert response.status_code == 200
    data = response.json()
    for opp in data["data"]:
        assert opp["confidence"] == "HIGH"


@pytest.mark.asyncio
async def test_get_opportunity_by_valid_id(async_client):
    response = await async_client.get(f"/api/v1/opportunities/{OPP_ID}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_opportunity_valid_id_returns_correct_opportunity(async_client):
    response = await async_client.get(f"/api/v1/opportunities/{OPP_ID}")
    data = response.json()
    assert data["id"] == OPP_ID


@pytest.mark.asyncio
async def test_get_opportunity_nonexistent_id_returns_404(async_client):
    response = await async_client.get("/api/v1/opportunities/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_refresh_opportunity_returns_200(async_client):
    response = await async_client.post(f"/api/v1/opportunities/{OPP_ID}/refresh")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_refresh_opportunity_has_run_id(async_client):
    response = await async_client.post(f"/api/v1/opportunities/{OPP_ID}/refresh")
    data = response.json()
    assert "run_id" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Actions
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_actions_returns_200(async_client):
    response = await async_client.get("/api/v1/actions")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_actions_response_shape(async_client):
    response = await async_client.get("/api/v1/actions")
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data


@pytest.mark.asyncio
async def test_list_actions_filter_by_status_todo(async_client):
    response = await async_client.get("/api/v1/actions?status=TODO")
    assert response.status_code == 200
    data = response.json()
    for action in data["data"]:
        assert action["status"] == "TODO"


@pytest.mark.asyncio
async def test_update_action_returns_200(async_client):
    response = await async_client.put(
        f"/api/v1/actions/{ACTION_ID}",
        json={"status": "DONE"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_action_reflects_new_status(async_client):
    response = await async_client.put(
        f"/api/v1/actions/{ACTION_ID}",
        json={"status": "DONE"},
    )
    data = response.json()
    assert data["status"] == "DONE"


@pytest.mark.asyncio
async def test_update_action_nonexistent_id_returns_404(async_client):
    response = await async_client.put(
        "/api/v1/actions/nonexistent-id",
        json={"status": "DONE"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_draft_email_for_action_returns_200(async_client):
    response = await async_client.post(f"/api/v1/actions/{ACTION_ID}/draft-email")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_draft_email_for_action_has_run_id(async_client):
    response = await async_client.post(f"/api/v1/actions/{ACTION_ID}/draft-email")
    data = response.json()
    assert "run_id" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Profile
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_profile_returns_200(async_client):
    response = await async_client.get("/api/v1/profile")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_profile_has_required_fields(async_client):
    response = await async_client.get("/api/v1/profile")
    data = response.json()
    assert "user_id" in data
    assert "current_role" in data
    assert "target_roles" in data


@pytest.mark.asyncio
async def test_update_profile_returns_200(async_client):
    response = await async_client.put(
        "/api/v1/profile",
        json={"current_role": "Senior Consultant"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_profile_reflects_new_current_role(async_client):
    response = await async_client.put(
        "/api/v1/profile",
        json={"current_role": "Senior Consultant"},
    )
    data = response.json()
    assert data["current_role"] == "Senior Consultant"
