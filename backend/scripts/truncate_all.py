"""
Truncate all application data tables, preserving the users row so login still works.
Run once to get a clean slate: python scripts/truncate_all.py
"""
import asyncio
import asyncpg
import os
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

# Delete order respects FK constraints (children before parents)
TRUNCATE_ORDER = [
    "agent_runs",
    "outreach_emails",
    "actions",
    "opportunities",
    "signals",
    "career_profiles",
    "user_documents",
    "contacts",
    "companies",
]


async def main():
    url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(url, statement_cache_size=0)
    try:
        for table in TRUNCATE_ORDER:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            await conn.execute(f"DELETE FROM {table}")
            print(f"  {table}: deleted {count} rows")

        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"\n  users: kept {users_count} row(s) (login preserved)")
    finally:
        await conn.close()

    print("\nDone. All application data cleared.")


asyncio.run(main())
