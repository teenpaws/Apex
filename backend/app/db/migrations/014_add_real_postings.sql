-- Phase 14: Add real_postings JSONB column to opportunities table.
-- Null = not yet validated. [] = validated, no match. [{...}] = validated with postings.
ALTER TABLE opportunities
  ADD COLUMN IF NOT EXISTS real_postings JSONB DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_opportunities_real_postings_notnull
  ON opportunities ((real_postings IS NOT NULL))
  WHERE real_postings IS NOT NULL;
