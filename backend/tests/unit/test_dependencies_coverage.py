"""Coverage for app/core/dependencies.py — get_current_user dependency."""
import pytest
from fastapi import HTTPException

from app.core.dependencies import get_current_user, MOCK_USER


# ── Mock mode (USE_MOCK_DATA=true — set in conftest) ─────────────────────────

@pytest.mark.asyncio
async def test_get_current_user_mock_mode_no_token():
    """In mock mode, get_current_user returns MOCK_USER without any token."""
    user = await get_current_user(token=None)
    assert user == MOCK_USER


@pytest.mark.asyncio
async def test_get_current_user_mock_mode_with_token():
    """In mock mode, get_current_user ignores any token and returns MOCK_USER."""
    user = await get_current_user(token="any-token-at-all")
    assert user == MOCK_USER


@pytest.mark.asyncio
async def test_get_current_user_returns_dict():
    """Return value must be a dict."""
    user = await get_current_user(token=None)
    assert isinstance(user, dict)


@pytest.mark.asyncio
async def test_get_current_user_has_id():
    """Returned user dict must contain 'id' key."""
    user = await get_current_user(token=None)
    assert "id" in user


@pytest.mark.asyncio
async def test_get_current_user_has_email():
    """Returned user dict must contain 'email' key."""
    user = await get_current_user(token=None)
    assert "email" in user


@pytest.mark.asyncio
async def test_mock_user_sentinel_values():
    """MOCK_USER fixture has expected values used throughout the test suite."""
    assert MOCK_USER["id"] == "mock-user-id"
    assert "apex.ai" in MOCK_USER["email"]


# ── Non-mock mode paths (force USE_MOCK_DATA=false temporarily) ──────────────

@pytest.mark.asyncio
async def test_get_current_user_no_token_non_mock_raises_401(monkeypatch):
    """Without a token and not in mock mode, raises 401."""
    # Temporarily override USE_MOCK_DATA to false
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    # Clear the settings cache so the new env var is picked up
    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        from app.core.dependencies import get_current_user
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=None)
        assert exc_info.value.status_code == 401
    finally:
        monkeypatch.setenv("USE_MOCK_DATA", "true")
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_non_mock_raises_401(monkeypatch):
    """With an invalid token and not in mock mode, raises 401."""
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()

    try:
        from app.core.dependencies import get_current_user
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="garbage.jwt.token")
        assert exc_info.value.status_code == 401
    finally:
        monkeypatch.setenv("USE_MOCK_DATA", "true")
        get_settings.cache_clear()
