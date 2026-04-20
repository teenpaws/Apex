"""Unit tests for production-specific Settings fields."""
import os
from unittest.mock import patch


def _fresh_settings(**env_overrides):
    """Instantiate Settings with patched env vars, bypassing the .env file and lru_cache."""
    from app.core.config import Settings
    with patch.dict(os.environ, {k: str(v) for k, v in env_overrides.items()}, clear=False):
        return Settings(_env_file=None)


def test_environment_defaults_to_development():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ENVIRONMENT", None)
        s = _fresh_settings()
    assert s.ENVIRONMENT == "development"


def test_json_logs_off_by_default():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("JSON_LOGS", None)
        s = _fresh_settings()
    assert s.JSON_LOGS is False


def test_log_level_defaults_to_info():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("LOG_LEVEL", None)
        s = _fresh_settings()
    assert s.LOG_LEVEL == "INFO"


def test_allowed_origins_default_contains_localhost():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ALLOWED_ORIGINS", None)
        s = _fresh_settings()
    assert any("localhost" in o for o in s.ALLOWED_ORIGINS)


def test_prod_environment_override():
    s = _fresh_settings(ENVIRONMENT="production", JSON_LOGS="true", LOG_LEVEL="WARNING")
    assert s.ENVIRONMENT == "production"
    assert s.JSON_LOGS is True
    assert s.LOG_LEVEL == "WARNING"


def test_allowed_origins_can_be_overridden():
    s = _fresh_settings(ALLOWED_ORIGINS='["https://app.apex.ai"]')
    assert s.ALLOWED_ORIGINS == ["https://app.apex.ai"]
