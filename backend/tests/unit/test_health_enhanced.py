"""Unit tests for enhanced health endpoint (environment field)."""
import pytest


@pytest.mark.asyncio
async def test_health_includes_environment(async_client):
    response = await async_client.get("/api/v1/health")
    data = response.json()
    assert "environment" in data, "health response must include environment field"
    assert data["environment"] == "development"


@pytest.mark.asyncio
async def test_health_all_fields_present(async_client):
    response = await async_client.get("/api/v1/health")
    data = response.json()
    required = {"status", "version", "mock_mode", "environment"}
    missing = required - set(data.keys())
    assert not missing, f"health response missing fields: {missing}"
