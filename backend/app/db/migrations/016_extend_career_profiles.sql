-- Migration 016: Extend career_profiles with resume-extracted fields (Phase 15)

ALTER TABLE career_profiles
  ADD COLUMN IF NOT EXISTS years_of_experience  int,
  ADD COLUMN IF NOT EXISTS seniority_band       text
      CHECK (seniority_band IN ('ANALYST', 'ASSOCIATE', 'MANAGER', 'DIRECTOR', 'VP_PLUS')),
  ADD COLUMN IF NOT EXISTS education_json       jsonb,
  ADD COLUMN IF NOT EXISTS work_history_json    jsonb,
  ADD COLUMN IF NOT EXISTS key_achievements_json jsonb,
  ADD COLUMN IF NOT EXISTS raw_resume_text      text,
  ADD COLUMN IF NOT EXISTS profile_source       text NOT NULL DEFAULT 'MANUAL'
      CHECK (profile_source IN ('MANUAL', 'RESUME', 'BOTH')),
  ADD COLUMN IF NOT EXISTS last_analyzed_at     timestamptz,
  ADD COLUMN IF NOT EXISTS extraction_staging_json jsonb;

COMMENT ON COLUMN career_profiles.seniority_band IS 'ANALYST|ASSOCIATE|MANAGER|DIRECTOR|VP_PLUS extracted from resume.';
COMMENT ON COLUMN career_profiles.extraction_staging_json IS 'Pending ProfileExtractor output awaiting user approval — cleared after approve.';
