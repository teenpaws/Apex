"""Quick view of where the pipeline is right now."""
import asyncio, asyncpg, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()


async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'), statement_cache_size=0)
    try:
        total = await conn.fetchval("SELECT COUNT(*) FROM signals")
        unprocessed = await conn.fetchval("SELECT COUNT(*) FROM signals WHERE processed_at IS NULL")
        processed = await conn.fetchval("SELECT COUNT(*) FROM signals WHERE processed_at IS NOT NULL")

        types = await conn.fetch(
            "SELECT type, COUNT(*) as n FROM signals "
            "WHERE processed_at IS NOT NULL GROUP BY type ORDER BY n DESC"
        )
        relevance = await conn.fetchrow(
            "SELECT COUNT(*) FILTER (WHERE relevance_score >= 0.4) as relevant, "
            "       COUNT(*) FILTER (WHERE relevance_score < 0.4) as low_rel "
            "FROM signals WHERE processed_at IS NOT NULL"
        )

        opps = await conn.fetchval("SELECT COUNT(*) FROM opportunities")
        actions = await conn.fetchval("SELECT COUNT(*) FROM actions")
        runs = await conn.fetch(
            "SELECT agent_name, status, COUNT(*) as n FROM agent_runs "
            "GROUP BY agent_name, status ORDER BY agent_name, status"
        )

        print(f"=== SIGNALS ===")
        print(f"  total:        {total}")
        print(f"  processed:    {processed}")
        print(f"  unprocessed:  {unprocessed}")
        print(f"\n  By type (processed only):")
        for r in types:
            print(f"    {r['type']:20} {r['n']}")
        print(f"\n  Relevance:")
        print(f"    >= 0.4 (will become opportunities): {relevance['relevant']}")
        print(f"    <  0.4 (filtered out):              {relevance['low_rel']}")

        print(f"\n=== DOWNSTREAM ===")
        print(f"  opportunities: {opps}")
        print(f"  actions:       {actions}")

        print(f"\n=== AGENT RUNS ===")
        if runs:
            for r in runs:
                print(f"  {r['agent_name']:25} {r['status']:10} {r['n']}")
        else:
            print(f"  (none yet)")
    finally:
        await conn.close()


asyncio.run(main())
