-- Migration 006: Create signals table
-- Raw market intelligence events ingested from external sources.
-- Classified by Signal Classifier agent; linked to opportunities via signal_ids[].

CREATE TABLE IF NOT EXISTS signals (
    id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id          uuid REFERENCES companies(id) ON DELETE SET NULL,
    type                text NOT NULL,          -- FUNDING|EXEC_HIRE|EXPANSION|LAYOFF|JOB_POSTING_PATTERN|MA|CONTRACT|EARNINGS
    source              text,
    title               text,
    description         text,
    raw_data_json       jsonb NOT NULL DEFAULT '{}',
    signal_date         timestamptz,
    relevance_score     float,
    processed_at        timestamptz,
    embedding           vector(1536),
    is_duplicate        bool NOT NULL DEFAULT false,
    dedup_hash          text UNIQUE,
    created_at          timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE signals IS 'Market intelligence events — funding rounds, exec hires, expansions, etc.';
COMMENT ON COLUMN signals.type IS 'Signal category: FUNDING|EXEC_HIRE|EXPANSION|LAYOFF|JOB_POSTING_PATTERN|MA|CONTRACT|EARNINGS';
COMMENT ON COLUMN signals.relevance_score IS 'Float 0–1 from Signal Classifier agent. <0.4 = low-relevance, pipeline stops.';
COMMENT ON COLUMN signals.embedding IS 'OpenAI text-embedding-3-small (1536 dims) for similarity-based opportunity matching.';
COMMENT ON COLUMN signals.is_duplicate IS 'True if duplicate detected via dedup_hash. Kept for debugging, not shown to user.';
COMMENT ON COLUMN signals.dedup_hash IS 'SHA-256 of (source + url + signal_date) — unique constraint prevents duplicate ingestion.';
