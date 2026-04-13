"""
Integration tests for Phase 9 endpoints:
  GET /api/v1/analytics/dashboard
  GET /api/v1/analytics/costs
  GET /api/v1/agents/runs
  GET /api/v1/agents/run-status/{run_id}

Runs against the FastAPI app with USE_MOCK_DATA=true (set in conftest.py).
"""

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Analytics
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_analytics_dashboard_returns_200(async_client):
    response = await async_client.get("/api/v1/analytics/dashboard")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_analytics_dashboard_response_shape(async_client):
    response = await async_client.get("/api/v1/analytics/dashboard")
    data = response.json()
    assert "signals_this_week" in data
    assert "new_opportunities" in data
    assert "actions_completed" in data
    assert "pipeline_stages" in data


@pytest.mark.asyncio
async def test_analytics_dashboard_pipeline_stages_shape(async_client):
    response = await async_client.get("/api/v1/analytics/dashboard")
    stages = response.json()["pipeline_stages"]
    assert "signals" in stages
    assert "opportunities" in stages
    assert "actions" in stages
    assert "outreach" in stages


@pytest.mark.asyncio
async def test_analytics_dashboard_values_are_ints(async_client):
    response = await async_client.get("/api/v1/analytics/dashboard")
    data = response.json()
    assert isinstance(data["signals_this_week"], int)
    assert isinstance(data["new_opportunities"], int)
    assert isinstance(data["actions_completed"], int)


@pytest.mark.asyncio
async def test_analytics_costs_returns_200(async_client):
    response = await async_client.get("/api/v1/analytics/costs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_analytics_costs_returns_list(async_client):
    response = await async_client.get("/api/v1/analytics/costs")
    data = response.json()
    # In mock mode this is an empty list
    assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════════════════
# Agents
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_agents_runs_returns_200(async_client):
    response = await async_client.get("/api/v1/agents/runs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_agents_runs_returns_list(async_client):
    response = await async_client.get("/api/v1/agents/runs")
    data = response.json()
    # In mock mode this is an empty list
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_agents_run_status_returns_200(async_client):
    response = await async_client.get("/api/v1/agents/run-status/test-run-123")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_agents_run_status_response_shape(async_client):
    response = await async_client.get("/api/v1/agents/run-status/test-run-123")
    data = response.json()
    assert "run_id" in data
    assert "status" in data
    assert "progress" in data


@pytest.mark.asyncio
async def test_agents_run_status_mock_returns_success(async_client):
    response = await async_client.get("/api/v1/agents/run-status/any-id")
    data = response.json()
    # In mock mode, all run-status calls immediately return SUCCESS
    assert data["status"] == "SUCCESS"
    assert data["progress"] == 100
