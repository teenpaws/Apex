"""
Apex platform configuration — reads all environment variables via Pydantic Settings.

Usage:
    from app.core.config import get_settings
    settings = get_settings()
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    APP_VERSION: str = "1.0.0"

    # ── Database / Supabase ───────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/apex"
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_ANON_KEY: str = "placeholder-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "placeholder-service-role-key"

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = "placeholder-anthropic-key"
    OPENAI_API_KEY: str = "placeholder-openai-key"

    # ── External Data APIs ────────────────────────────────────────────────────
    PROXYCURL_API_KEY: str = "placeholder-proxycurl-key"
    NEWS_API_KEY: str = "placeholder-newsapi-key"
    CRUNCHBASE_API_KEY: str = "placeholder-crunchbase-key"
    DEALROOM_API_KEY: str = "placeholder-dealroom-key"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # ── Gmail OAuth ───────────────────────────────────────────────────────────
    GMAIL_CLIENT_ID: str = "placeholder-gmail-client-id"
    GMAIL_CLIENT_SECRET: str = "placeholder-gmail-client-secret"
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/v1/outreach/oauth/callback"

    # ── Development Flags ─────────────────────────────────────────────────────
    # True  → no real API/DB calls; uses fixture files and mock responses
    # False → live mode; requires real keys and a running Supabase project
    MOCK_AGENTS: bool = True
    USE_MOCK_DATA: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
