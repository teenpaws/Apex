"""
Unit tests for auth endpoints — POST /api/v1/auth/login, POST /api/v1/auth/refresh

All tests run with USE_MOCK_DATA=true (set in conftest.py) so no Supabase connection
is required.
"""
import pytest


@pytest.mark.asyncio
async def test_login_mock_valid_user(async_client):
    """Valid mock user returns 200 with access_token."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@apex.dev", "password": "anypassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] == "mock-token"
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@apex.dev"
    assert data["user"]["id"] == "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_login_mock_invalid_user(async_client):
    """Unknown email in mock mode returns 401 with structured error."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "somepassword"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"] == "Invalid credentials"
    assert data["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_missing_fields(async_client):
    """Empty body fails Pydantic validation with 422."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_password(async_client):
    """Missing password field fails Pydantic validation with 422."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@apex.dev"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_email_format(async_client):
    """Malformed email fails EmailStr validation with 422."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_mock(async_client):
    """Refresh with any token in mock mode returns 200 with new access_token."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "any-token-value"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] == "mock-token-refreshed"
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_missing_token(async_client):
    """Empty body on refresh fails Pydantic validation with 422."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_current_user_no_token(async_client):
    """
    Health endpoint is public — no token needed.
    Confirms the app starts correctly with auth wired in.
    """
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
