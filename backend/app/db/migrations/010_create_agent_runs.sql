-- Migration 010: Create agent_runs table
-- Audit trail for ALL AI agent invocations — required by architecture.
-- Used for cost tracking, debugging, prompt versioning, and rollback.

CREATE TABLE IF NOT EXISTS agent_runs (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_name      text NOT NULL,
    model_used      text NOT NULL,
    input_hash      text,
    output_hash     text,
    tokens_in       int,
    tokens_out      int,
    cost_usd        float,
    duration_ms     int,
    status          text NOT NULL DEFAULT 'SUCCESS', -- SUCCESS|FAILED|RETRIED
    error_message   text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE agent_runs IS 'Immutable audit log for every Claude agent invocation — cost, tokens, hashes, status.';
COMMENT ON COLUMN agent_runs.input_hash IS 'SHA-256 of the full prompt input — for dedup and prompt version tracking.';
COMMENT ON COLUMN agent_runs.output_hash IS 'SHA-256 of the agent output — for content change detection.';
COMMENT ON COLUMN agent_runs.cost_usd IS 'Cost in USD calculated at write time from token counts and model pricing.';
COMMENT ON COLUMN agent_runs.error_message IS 'Populated only on FAILED status — full error/traceback for debugging.';
