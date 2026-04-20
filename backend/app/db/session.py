"""
Async database session management for the Apex backend.

Provides:
- Async SQLAlchemy engine (asyncpg driver) — lazily initialized
- AsyncSession factory
- get_db() — FastAPI dependency that yields a session
- get_supabase_client() — returns supabase-py client or None (placeholder creds)

Usage in FastAPI routes:
    from app.db.session import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        ...

NOTE: Engine creation is lazy — it does not happen at import time. This allows
the models to be imported freely in tests and mock mode without asyncpg installed.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── URL helpers ────────────────────────────────────────────────────────────────

def _build_async_db_url(database_url: str) -> str:
    """
    Convert a standard postgresql:// URL to the asyncpg driver URL.
    Also handles postgresql+asyncpg:// (already correct) and
    postgresql+psycopg2:// (swap the driver).
    """
    if "postgresql+asyncpg" in database_url:
        return database_url
    return database_url.replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    ).replace(
        "postgresql://", "postgresql+asyncpg://"
    )


def _is_placeholder_url(database_url: str) -> bool:
    """Return True if the DATABASE_URL still contains obvious placeholder values."""
    placeholder_indicators = [
        "placeholder",
        "password@localhost",
        "test:test@",
    ]
    return any(p in database_url for p in placeholder_indicators)


# ── Lazy engine + session factory ──────────────────────────────────────────────
# We defer engine creation to avoid ImportError on asyncpg at import time
# when running in mock mode (USE_MOCK_DATA=true) or during model-only tests.

_engine = None
_session_factory = None


def _get_engine():
    """Return (and lazily create) the async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine  # noqa: PLC0415

        settings = get_settings()
        async_url = _build_async_db_url(settings.DATABASE_URL)

        if _is_placeholder_url(settings.DATABASE_URL):
            logger.warning(
                "DATABASE_URL appears to be a placeholder (%s). "
                "DB operations will fail until a real Supabase connection string is provided. "
                "This is expected in development with USE_MOCK_DATA=true.",
                settings.DATABASE_URL,
            )

        _engine = create_async_engine(
            async_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def _get_session_factory():
    """Return (and lazily create) the async session factory."""
    global _session_factory
    if _session_factory is None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: PLC0415

        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


# ── Public API ──────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator:
    """
    FastAPI dependency — yields an AsyncSession and guarantees cleanup.

    Usage:
        @router.get("/")
        async def handler(db: AsyncSession = Depends(get_db)):
            result = await db.execute(...)
    """
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_db_client():
    """Alias for get_supabase_client — used by analytics and service modules."""
    return get_supabase_client()


def get_asyncpg_db_url() -> str:
    """Return the raw asyncpg-compatible DATABASE_URL for direct connections."""
    settings = get_settings()
    return settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://').replace('postgresql+psycopg2://', 'postgresql://')


def get_supabase_client():
    """
    Return a supabase-py client configured with project URL and service role key.

    Returns None with a warning when credentials are still placeholders
    (expected in dev/mock mode — no code changes needed when real keys arrive).

    Usage:
        supabase = get_supabase_client()
        if supabase:
            data = supabase.table("users").select("*").execute()
    """
    settings = get_settings()
    supabase_url = settings.SUPABASE_URL
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY

    if "placeholder" in supabase_url or "placeholder" in service_key:
        logger.warning(
            "Supabase credentials are placeholders. "
            "get_supabase_client() returning None. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env to enable."
        )
        return None

    try:
        from supabase import create_client, Client  # noqa: PLC0415
        client: Client = create_client(supabase_url, service_key)
        return client
    except ImportError:
        logger.error("supabase-py is not installed. Run: pip install supabase")
        return None
    except Exception as exc:
        logger.error("Failed to create Supabase client: %s", exc)
        return None
