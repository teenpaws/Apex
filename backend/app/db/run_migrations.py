"""
Run all SQL migrations against the Supabase database in order.

Usage (from backend/ directory):
    python -m app.db.run_migrations
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def run_migrations(database_url: str):
    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg required.", file=sys.stderr)
        sys.exit(1)

    db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to database...")
    conn = await asyncpg.connect(db_url, statement_cache_size=0)

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    print(f"Found {len(migration_files)} migration files.\n")

    for mf in migration_files:
        sql = mf.read_text(encoding="utf-8")
        print(f"  Running {mf.name} ...", end=" ")
        try:
            await conn.execute(sql)
            print("OK")
        except Exception as exc:
            print(f"WARNING: {exc}")

    await conn.close()
    print("\nMigrations complete.")


async def main():
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from app.core.config import get_settings
    s = get_settings()
    await run_migrations(s.DATABASE_URL)


if __name__ == "__main__":
    asyncio.run(main())
