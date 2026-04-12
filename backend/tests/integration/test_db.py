"""
Integration tests for the Apex database layer.

All tests are skipped when USE_MOCK_DATA=true (the dev default).
They are designed to run against a real Supabase Postgres instance once
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and DATABASE_URL are configured.

To run (after Supabase creds are set):
    USE_MOCK_DATA=false python -m pytest tests/integration/test_db.py -v
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from app.core.config import get_settings

settings = get_settings()

# ── Skip guard ─────────────────────────────────────────────────────────────────
# All tests below require a live DB — skip in mock mode.

pytestmark = pytest.mark.skipif(
    settings.USE_MOCK_DATA,
    reason="Requires real Supabase connection (USE_MOCK_DATA=false)",
)

# ── Expected tables ────────────────────────────────────────────────────────────

EXPECTED_TABLES = [
    "users",
    "career_profiles",
    "companies",
    "contacts",
    "signals",
    "opportunities",
    "actions",
    "outreach_emails",
    "agent_runs",
]

# Tables with user_id that must have RLS enabled
RLS_TABLES = [
    "users",
    "career_profiles",
    "signals",
    "opportunities",
    "actions",
    "outreach_emails",
    "agent_runs",
]


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def db_conn():
    """
    Provide a raw asyncpg connection to the test database.
    Uses DATABASE_URL from settings (expected to point at Supabase).
    """
    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed — cannot run DB integration tests")

    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    yield conn
    await conn.close()


# ── Tests ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tables_exist(db_conn):
    """
    Verify all 9 expected tables are present in the public schema.
    Queries information_schema.tables — available to all Postgres roles.
    """
    rows = await db_conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        """
    )
    existing_tables = {row["table_name"] for row in rows}

    for table in EXPECTED_TABLES:
        assert table in existing_tables, (
            f"Expected table '{table}' not found in public schema. "
            f"Run migrations 002–010 in the Supabase SQL editor."
        )


@pytest.mark.asyncio
async def test_rls_enabled(db_conn):
    """
    Verify Row-Level Security is enabled on all user-scoped tables.
    Queries pg_tables.rowsecurity flag.
    """
    rows = await db_conn.fetch(
        """
        SELECT tablename, rowsecurity
        FROM pg_tables
        WHERE schemaname = 'public'
        """
    )
    rls_status = {row["tablename"]: row["rowsecurity"] for row in rows}

    for table in RLS_TABLES:
        assert table in rls_status, f"Table '{table}' not found in pg_tables"
        assert rls_status[table] is True, (
            f"RLS is NOT enabled on '{table}'. "
            f"Run migration 011_create_rls_policies.sql."
        )


@pytest.mark.asyncio
async def test_career_profiles_has_embedding(db_conn):
    """
    Verify career_profiles.embedding column exists and has type 'vector'.
    pgvector creates a custom 'vector' type — check column_data_type.
    """
    row = await db_conn.fetchrow(
        """
        SELECT udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'career_profiles'
          AND column_name  = 'embedding'
        """
    )
    assert row is not None, (
        "Column 'career_profiles.embedding' not found. "
        "Check migration 005_create_career_profiles.sql."
    )
    assert row["udt_name"] == "vector", (
        f"Expected column type 'vector', got '{row['udt_name']}'. "
        "Make sure the pgvector extension is enabled (migration 001)."
    )


@pytest.mark.asyncio
async def test_signals_has_embedding(db_conn):
    """
    Verify signals.embedding column exists and has type 'vector'.
    """
    row = await db_conn.fetchrow(
        """
        SELECT udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'signals'
          AND column_name  = 'embedding'
        """
    )
    assert row is not None, (
        "Column 'signals.embedding' not found. "
        "Check migration 006_create_signals.sql."
    )
    assert row["udt_name"] == "vector", (
        f"Expected column type 'vector', got '{row['udt_name']}'. "
        "Make sure the pgvector extension is enabled (migration 001)."
    )


@pytest.mark.asyncio
async def test_signals_dedup_hash_unique(db_conn):
    """
    Verify dedup_hash column on signals table has a unique constraint.
    """
    row = await db_conn.fetchrow(
        """
        SELECT constraint_type
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
        WHERE tc.table_schema  = 'public'
          AND tc.table_name    = 'signals'
          AND kcu.column_name  = 'dedup_hash'
          AND tc.constraint_type = 'UNIQUE'
        """
    )
    assert row is not None, (
        "UNIQUE constraint on 'signals.dedup_hash' not found. "
        "Check migration 006_create_signals.sql."
    )


@pytest.mark.asyncio
async def test_seed_data_loads():
    """
    Verify the seed script runs without exception in dry-run mode.
    Imports and calls print_dry_run() directly — no subprocess needed.
    """
    from app.db.seeds.seed_dev import print_dry_run, build_seed_statements

    # Verify dry-run builds statements without error
    stmts = build_seed_statements()
    assert len(stmts) > 0, "build_seed_statements() returned empty list"

    # Verify expected counts
    from app.db.seeds.seed_dev import USERS, COMPANIES, SIGNALS, OPPORTUNITIES, ACTIONS
    assert len(USERS) == 1
    assert len(COMPANIES) == 5
    assert len(SIGNALS) == 10
    assert len(OPPORTUNITIES) == 3
    assert len(ACTIONS) == 5

    total = len(USERS) + len(COMPANIES) + len(SIGNALS) + len(OPPORTUNITIES) + len(ACTIONS)
    assert len(stmts) == total, f"Expected {total} statements, got {len(stmts)}"

    # Ensure dry-run print doesn't raise (captures stdout)
    import io
    from contextlib import redirect_stdout
    with redirect_stdout(io.StringIO()):
        print_dry_run()  # Must not raise


@pytest.mark.asyncio
async def test_agent_runs_no_update_policy(db_conn):
    """
    Verify agent_runs table has no UPDATE RLS policy (audit trail is immutable).
    """
    rows = await db_conn.fetch(
        """
        SELECT polname, polcmd
        FROM pg_policy
        WHERE polrelid = 'agent_runs'::regclass
        """
    )
    policy_commands = {row["polcmd"] for row in rows}

    # 'w' = UPDATE in pg_policy.polcmd encoding
    assert "w" not in policy_commands, (
        "agent_runs table has an UPDATE RLS policy — audit trail must be immutable. "
        "Remove UPDATE policy from migration 011."
    )
