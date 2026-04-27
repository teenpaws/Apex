"""Print the full career_profiles + work_history + extraction data for the user."""
import asyncio, asyncpg, json, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()


async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'), statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            'SELECT * FROM career_profiles ORDER BY updated_at DESC LIMIT 1'
        )
        if not row:
            print("No career_profiles row.")
            return

        print("=== MANUAL FIELDS ===")
        print(f"current_role:    {row['current_role']}")
        print(f"target_roles:    {list(row['target_roles'] or [])}")
        print(f"industries:      {list(row['industries'] or [])}")
        print(f"aspirations:     {row['aspirations_text']}")
        print(f"\n=== EXTRACTED ===")
        print(f"seniority_band:  {row['seniority_band']}")
        print(f"years_of_exp:    {row['years_of_experience']}")
        print(f"profile_source:  {row['profile_source']}")

        for jcol in ['education_json', 'work_history_json', 'key_achievements_json']:
            val = row[jcol]
            if val:
                parsed = json.loads(val) if isinstance(val, str) else val
                print(f"\n--- {jcol} ---")
                print(json.dumps(parsed, indent=2))

        # Also print the resume text snippet
        if row['raw_resume_text']:
            print(f"\n--- raw_resume_text (first 2000 chars) ---")
            print(row['raw_resume_text'][:2000])
    finally:
        await conn.close()


asyncio.run(main())
