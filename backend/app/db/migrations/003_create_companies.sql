-- Migration 003: Create companies table
-- Stores company profiles that signals and opportunities reference.
-- Not user-scoped (shared across users in cohort model) — enrichment data cached here.

CREATE TABLE IF NOT EXISTS companies (
    id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                text NOT NULL,
    domain              text,
    industry            text,
    size_range          text,
    location            text,
    linkedin_url        text,
    enrichment_json     jsonb NOT NULL DEFAULT '{}',
    last_enriched_at    timestamptz
);

COMMENT ON TABLE companies IS 'Company profiles used as targets for signals and opportunities.';
COMMENT ON COLUMN companies.linkedin_url IS 'Required for Proxycurl enrichment lookups.';
COMMENT ON COLUMN companies.enrichment_json IS 'Cached Proxycurl / Crunchbase enrichment payload.';
COMMENT ON COLUMN companies.last_enriched_at IS 'Timestamp of last Proxycurl enrichment run.';
