"""Apply migrations 014-017 to the live Supabase DB."""
import asyncio
import asyncpg
import os
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

MIGRATIONS = [
    ("014 - real_postings on opportunities", """
        ALTER TABLE opportunities
          ADD COLUMN IF NOT EXISTS real_postings JSONB DEFAULT NULL;

        CREATE INDEX IF NOT EXISTS idx_opportunities_real_postings_notnull
          ON opportunities ((real_postings IS NOT NULL))
          WHERE real_postings IS NOT NULL;
    """),

    ("015 - user_documents table", """
        CREATE TABLE IF NOT EXISTS user_documents (
            id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename            text NOT NULL,
            file_type           text NOT NULL CHECK (file_type IN ('PDF', 'DOCX')),
            doc_type            text NOT NULL CHECK (doc_type IN ('RESUME', 'COVER_LETTER', 'OTHER')),
            storage_path        text,
            extracted_text      text,
            target_context      text,
            extraction_status   text NOT NULL DEFAULT 'PENDING'
                                CHECK (extraction_status IN ('PENDING', 'EXTRACTED', 'ANALYZED', 'FAILED')),
            staging_json        jsonb,
            created_at          timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_documents_doc_type ON user_documents(user_id, doc_type);
        ALTER TABLE user_documents ENABLE ROW LEVEL SECURITY;
    """),

    ("015b - RLS policies for user_documents", """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename='user_documents' AND policyname='user_documents_select_own'
          ) THEN
            CREATE POLICY user_documents_select_own ON user_documents
              FOR SELECT USING (user_id = auth.uid()::uuid);
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename='user_documents' AND policyname='user_documents_insert_own'
          ) THEN
            CREATE POLICY user_documents_insert_own ON user_documents
              FOR INSERT WITH CHECK (user_id = auth.uid()::uuid);
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename='user_documents' AND policyname='user_documents_update_own'
          ) THEN
            CREATE POLICY user_documents_update_own ON user_documents
              FOR UPDATE USING (user_id = auth.uid()::uuid);
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename='user_documents' AND policyname='user_documents_delete_own'
          ) THEN
            CREATE POLICY user_documents_delete_own ON user_documents
              FOR DELETE USING (user_id = auth.uid()::uuid);
          END IF;
        END $$;
    """),

    ("016 - Phase 15 columns on career_profiles", """
        ALTER TABLE career_profiles
          ADD COLUMN IF NOT EXISTS years_of_experience     int,
          ADD COLUMN IF NOT EXISTS seniority_band          text
              CHECK (seniority_band IN ('ANALYST', 'ASSOCIATE', 'MANAGER', 'DIRECTOR', 'VP_PLUS')),
          ADD COLUMN IF NOT EXISTS education_json          jsonb,
          ADD COLUMN IF NOT EXISTS work_history_json       jsonb,
          ADD COLUMN IF NOT EXISTS key_achievements_json   jsonb,
          ADD COLUMN IF NOT EXISTS raw_resume_text         text,
          ADD COLUMN IF NOT EXISTS profile_source          text NOT NULL DEFAULT 'MANUAL'
              CHECK (profile_source IN ('MANUAL', 'RESUME', 'BOTH')),
          ADD COLUMN IF NOT EXISTS last_analyzed_at        timestamptz,
          ADD COLUMN IF NOT EXISTS extraction_staging_json jsonb;
    """),

    ("017 - rename positioning_notes to approach_angle", """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'opportunities' AND column_name = 'positioning_notes'
          ) THEN
            ALTER TABLE opportunities RENAME COLUMN positioning_notes TO approach_angle;
          END IF;
        END $$;
    """),

    ("018 - intended_effect on actions", """
        ALTER TABLE actions
          ADD COLUMN IF NOT EXISTS intended_effect text;
    """),

    ("019 - channel on outreach_emails", """
        ALTER TABLE outreach_emails
          ADD COLUMN IF NOT EXISTS channel text NOT NULL DEFAULT 'EMAIL'
              CHECK (channel IN ('EMAIL', 'LINKEDIN'));
    """),
]


async def main():
    url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(url, statement_cache_size=0)
    try:
        for name, sql in MIGRATIONS:
            print(f"Running: {name} ... ", end='', flush=True)
            try:
                await conn.execute(sql)
                print("OK")
            except Exception as e:
                print(f"ERROR: {e}")
    finally:
        await conn.close()

    print("\nVerifying columns after migration:")
    conn = await asyncpg.connect(url, statement_cache_size=0)
    try:
        for tbl in ['opportunities', 'career_profiles', 'user_documents', 'actions', 'outreach_emails']:
            cols = await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name=$1 ORDER BY ordinal_position", tbl
            )
            print(f"  {tbl}: {[r['column_name'] for r in cols]}")
    finally:
        await conn.close()


asyncio.run(main())
