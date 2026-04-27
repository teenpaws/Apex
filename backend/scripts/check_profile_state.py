"""Quick view of profile/document state for the current user."""
import asyncio, asyncpg, os, sys, json
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()


async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'), statement_cache_size=0)
    try:
        users = await conn.fetch("SELECT id, email FROM users")
        print(f"Users: {len(users)}")
        for u in users:
            print(f"  {u['email']}  ({u['id']})")

        profiles = await conn.fetch(
            'SELECT user_id, "current_role", target_roles, industries, '
            'aspirations_text, seniority_band, years_of_experience, '
            'extraction_staging_json IS NOT NULL as has_staging, '
            'last_analyzed_at FROM career_profiles'
        )
        print(f"\nCareer profiles: {len(profiles)}")
        for p in profiles:
            print(f"  current_role: {p['current_role']}")
            print(f"  target_roles: {p['target_roles']}")
            print(f"  industries: {p['industries']}")
            print(f"  aspirations: {(p['aspirations_text'] or '')[:80]}")
            print(f"  seniority: {p['seniority_band']}, yoe: {p['years_of_experience']}")
            print(f"  has_staging: {p['has_staging']}, last_analyzed: {p['last_analyzed_at']}")

        docs = await conn.fetch(
            "SELECT id, filename, doc_type, target_context, extraction_status, "
            "char_length(extracted_text) as text_len, created_at "
            "FROM user_documents ORDER BY created_at"
        )
        print(f"\nUser documents: {len(docs)}")
        for d in docs:
            print(f"  [{d['doc_type']}] {d['filename']} — {d['extraction_status']}, "
                  f"{d['text_len']} chars, ctx={d['target_context']}")

        runs = await conn.fetch(
            "SELECT agent_name, status, error_message, created_at "
            "FROM agent_runs ORDER BY created_at DESC LIMIT 5"
        )
        print(f"\nRecent agent_runs: {len(runs)}")
        for r in runs:
            print(f"  {r['created_at']} | {r['agent_name']} | {r['status']} "
                  f"{('| ' + r['error_message'][:60]) if r['error_message'] else ''}")
    finally:
        await conn.close()


asyncio.run(main())
