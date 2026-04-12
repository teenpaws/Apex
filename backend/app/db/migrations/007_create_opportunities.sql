-- Migration 007: Create opportunities table
-- AI-predicted hiring needs — output of the Opportunity Predictor agent.
-- Each opportunity links back to the signals that triggered it.

CREATE TABLE IF NOT EXISTS opportunities (
    id                      uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id              uuid REFERENCES companies(id) ON DELETE SET NULL,
    predicted_role          text,
    confidence              text NOT NULL,          -- HIGH|MEDIUM|SPECULATIVE
    timeline_weeks          int,
    why_fit                 text,
    positioning_notes       text,
    predicted_salary_range  text,
    fit_score               float,
    key_contact_id          uuid REFERENCES contacts(id) ON DELETE SET NULL,
    signal_ids              uuid[] NOT NULL DEFAULT '{}',
    status                  text NOT NULL DEFAULT 'PREDICTED', -- PREDICTED|APPROACHED|INTERVIEWING|CLOSED
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE opportunities IS 'AI-predicted roles — output of Opportunity Predictor agent based on market signals.';
COMMENT ON COLUMN opportunities.confidence IS 'Confidence band: HIGH|MEDIUM|SPECULATIVE based on signal strength.';
COMMENT ON COLUMN opportunities.fit_score IS 'Career Fit Scorer output (0–100). NULL until scorer runs.';
COMMENT ON COLUMN opportunities.signal_ids IS 'Denormalized array of signal UUIDs that triggered this opportunity (v1.0). Normalize in v1.5.';
COMMENT ON COLUMN opportunities.key_contact_id IS 'Best contact to approach at this company for this role.';
