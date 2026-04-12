-- Migration 004: Create contacts table
-- People at target companies — enriched via Proxycurl on demand.
-- Linked to companies; used by outreach_emails and actions.

CREATE TABLE IF NOT EXISTS contacts (
    id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          uuid REFERENCES companies(id) ON DELETE SET NULL,
    name                text NOT NULL,
    title               text,
    linkedin_url        text,
    email               text,
    enrichment_json     jsonb NOT NULL DEFAULT '{}',
    last_enriched_at    timestamptz
);

COMMENT ON TABLE contacts IS 'People at target companies — enriched via Proxycurl.';
COMMENT ON COLUMN contacts.enrichment_json IS 'Full Proxycurl profile payload (work history, skills, etc).';
