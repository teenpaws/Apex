"""Coverage gap-fill for app/api/v1/auth.py — live mode paths using respx HTTP mocking."""
import pytest
import respx
import httpx


# ── Login endpoint — live mode ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_live_mode_success(async_client, monkeypatch):
    """Successful login in live mode returns access_token + user."""
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        supabase_url = "https://placeholder.supabase.co"
        with respx.mock:
            respx.post(
                f"{supabase_url}/auth/v1/token?grant_type=password"
            ).mock(return_value=httpx.Response(
                200,
                json={
                    "access_token": "live-token-abc",
                    "token_type": "bearer",
                    "user": {"id": "user-123", "email": "user@example.com"},
                }
            ))
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "secret"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "live-token-abc"
        assert data["user"]["id"] == "user-123"
    finally:
        monkeypatch.setenv("USE_MOCK_DATA", "true")
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_login_live_mode_invalid_credentials(async_client, monkeypatch):
    """Invalid credentials in live mode returns 401."""
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        supabase_url = "https://placeholder.supabase.co"
        with respx.mock:
            respx.post(
                f"{supabase_url}/auth/v1/token?grant_type=password"
            ).mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "bad@example.com", "password": "wrong"},
            )
        assert response.status_code == 401
    finally:
        monkeypatch.setenv("USE_MOCK_DATA", "true")
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_login_live_mode_service_unavailable(async_client, monkeypatch):
    """Network error to Supabase returns 503."""
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        supabase_url = "https://placeholder.supabase.co"
        with respx.mock:
            respx.post(
                f"{supabase_url}/auth/v1/token?grant_type=password"
            ).mock(side_effect=httpx.ConnectError("Connection refused"))
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "secret"},
            )
        assert response.status_code == 503
    finally:
        monkeypatch.setenv("USE_MOCK_DATA", "true")
        get_settings.cache_clear()


# ── Refresh endpoint — live mode ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_live_mode_success(async_client, monkeypatch):
    """Successful token refresh in live mode returns new access_token."""
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        supabase_url = "https://placeholder.supabase.co"
        with respx.mock:
            respx.post(
                f"{supabase_url}/auth/v1/token?grant_type=refresh_token"
            ).mock(return_value=httpx.Response(
                200,
                json={"access_token": "new-token-xyz", "token_type": "bearer"}
            ))
            response = await async_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new-token-xyz"
    finally:
        monkeypatch.setenv("USE_MOCK_DATA", "true")
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_refresh_live_mode_expired_token(async_client, monkeypatch):
    """Expired refresh token in live mode returns 401."""
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        supabase_url = "https://placeholder.supabase.co"
        with respx.mock:
            respx.post(
                f"{supabase_url}/auth/v1/token?grant_type=refresh_token"
            ).mock(return_value=httpx.Response(401, json={"error": "invalid_refresh_token"}))
            response = await async_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "expired-token"},
            )
        assert response.status_code == 401
    finally:
        monkeypatch.setenv("USE_MOCK_DATA", "true")
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_refresh_live_mode_service_unavailable(async_client, monkeypatch):
    """Network error to Supabase on refresh returns 503."""
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        supabase_url = "https://placeholder.supabase.co"
        with respx.mock:
            respx.post(
                f"{supabase_url}/auth/v1/token?grant_type=refresh_token"
            ).mock(side_effect=httpx.ConnectError("Connection refused"))
            response = await async_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "some-token"},
            )
        assert response.status_code == 503
    finally:
        monkeypatch.setenv("USE_MOCK_DATA", "true")
        get_settings.cache_clear()
