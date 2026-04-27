"""Seed only the companies table — preserves user profile / extracted data."""
import asyncio
import asyncpg
import os
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from app.db.seeds.seed_production import COMPANIES


async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'), statement_cache_size=0)
    try:
        for c in COMPANIES:
            await conn.execute(
                """INSERT INTO companies (name, domain, industry, size_range, location, linkedin_url, enrichment_json)
                   VALUES ($1, $2, $3, $4, $5, $6, '{}'::jsonb)
                   ON CONFLICT DO NOTHING""",
                c['name'], c['domain'], c['industry'], c['size_range'], c['location'], c['linkedin_url'],
            )
        count = await conn.fetchval("SELECT COUNT(*) FROM companies")
        print(f"Companies in DB: {count}")
        rows = await conn.fetch("SELECT name, industry FROM companies ORDER BY name")
        for r in rows:
            print(f"  - {r['name']} ({r['industry']})")
    finally:
        await conn.close()


asyncio.run(main())
