"""Unit tests for config/settings."""
import pytest
from app.core.config import get_settings


def test_settings_loads():
    settings = get_settings()
    assert settings.APP_VERSION == "1.0.0"
    assert settings.MOCK_AGENTS is True
    assert settings.USE_MOCK_DATA is True


def test_settings_mock_mode():
    settings = get_settings()
    assert settings.USE_MOCK_DATA is True, "Dev mode should have mock data enabled"
