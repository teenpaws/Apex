"""
Apex platform configuration — reads all environment variables via Pydantic Settings.

Usage:
    from app.core.config import get_settings
    settings = get_settings()
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── Database / Supabase ───────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/apex"
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_ANON_KEY: str = "placeholder-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "placeholder-service-role-key"

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = "placeholder-anthropic-key"
    OPENAI_API_KEY: str = "placeholder-openai-key"

    # ── Signal Sources (free tier — see CLAUDE.md Section 14) ────────────────
    NEWSDATA_API_KEY: str = "placeholder-newsdata-key"   # newsdata.io — 200 req/day free
    GNEWS_API_KEY: str = "placeholder-gnews-key"         # gnews.io — 100 req/day free (backup)
    # SEC EDGAR: no key needed — data.sec.gov is fully public

    # ── Contact Intelligence (PDL replaces Proxycurl, shut down July 2025) ───
    PDL_API_KEY: str = "placeholder-pdl-key"             # peopledatalabs.com — 1k free/mo
    HUNTER_API_KEY: str = "placeholder-hunter-key"       # hunter.io — 25 free/mo (email finding)

    # ── Adzuna Job Board (opportunity validation — free API) ──────────────────
    ADZUNA_APP_ID: str = "placeholder-adzuna-app-id"
    ADZUNA_APP_KEY: str = "placeholder-adzuna-app-key"
    ADZUNA_COUNTRY: str = "gb"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # ── Gmail OAuth ───────────────────────────────────────────────────────────
    GMAIL_CLIENT_ID: str = "placeholder-gmail-client-id"
    GMAIL_CLIENT_SECRET: str = "placeholder-gmail-client-secret"
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/v1/outreach/oauth/callback"

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = False  # True in production for structured log aggregation

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # ── Development Flags ─────────────────────────────────────────────────────
    # True  → no real API/DB calls; uses fixture files and mock responses
    # False → live mode; requires real keys and a running Supabase project
    MOCK_AGENTS: bool = True
    USE_MOCK_DATA: bool = True

    # ── Signal Classification Pipeline ───────────────────────────────────────
    # True  → keyword pre-filter eliminates ~40-60% of signals before AI call
    PRE_FILTER_ENABLED: bool = True
    # Number of signals per Claude Sonnet batch classify call (max 10)
    BATCH_CLASSIFY_SIZE: int = Field(default=10, ge=1, le=10)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
