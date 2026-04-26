-- Migration 017: Rename positioning_notes to approach_angle in opportunities (Phase 15)
-- Wrapped in DO block so it is safe to re-run (PG has no RENAME COLUMN IF EXISTS).

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'opportunities' AND column_name = 'positioning_notes'
  ) THEN
    ALTER TABLE opportunities RENAME COLUMN positioning_notes TO approach_angle;
    COMMENT ON COLUMN opportunities.approach_angle IS
      '1-sentence strategic seed from OpportunityPredictor for the PositioningAdvisor to elaborate on.';
  END IF;
END $$;
