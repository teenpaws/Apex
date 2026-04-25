-- Migration 017: Rename positioning_notes to approach_angle in opportunities (Phase 15)
-- positioning_notes was legacy name. approach_angle better reflects the purpose:
-- 1-sentence strategic seed from OpportunityPredictor for PositioningAdvisor to elaborate.

ALTER TABLE opportunities
  RENAME COLUMN positioning_notes TO approach_angle;

COMMENT ON COLUMN opportunities.approach_angle IS '1-sentence strategic seed from OpportunityPredictor for the PositioningAdvisor to elaborate on.';
