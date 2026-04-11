"""Integration test: health endpoint smoke test."""
import pytest


@pytest.mark.asyncio
async def test_health_returns_200(async_client):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(async_client):
    response = await async_client.get("/api/v1/health")
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "version" in data
    assert "mock_mode" in data


@pytest.mark.asyncio
async def test_health_mock_mode_true(async_client):
    """In dev, mock_mode should be true."""
    response = await async_client.get("/api/v1/health")
    data = response.json()
    assert data["mock_mode"] is True
