-- Apex Platform — Initial Schema
-- Generated from backend/app/db/migrations/ in numeric order
-- Paste this entire file into Supabase SQL Editor and click Run
-- Last updated: 2026-04-24

-- ============================================================
-- Migration: 001_enable_extensions.sql
-- ============================================================
-- Migration 001: Enable required Postgres extensions
-- Run this first in Supabase SQL editor

-- pgvector for 1536-dim embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Migration: 002_create_users.sql
-- ============================================================
-- Migration 002: Create users table
-- Core user account table — every row in the system scopes back to a user_id here.
-- Supabase Auth manages authentication; this table stores application-level profile data.

CREATE TABLE IF NOT EXISTS users (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           text UNIQUE NOT NULL,
    full_name       text,
    profile_json    jsonb NOT NULL DEFAULT '{}',
    preferences_json jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE users IS 'Application users — mirrors Supabase Auth users with app profile data.';
COMMENT ON COLUMN users.profile_json IS 'Freeform profile data (bio, social links, etc).';
COMMENT ON COLUMN users.preferences_json IS 'User preferences (notification settings, UI prefs, etc).';

-- ============================================================
-- Migration: 003_create_companies.sql
-- ============================================================
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

-- ============================================================
-- Migration: 004_create_contacts.sql
-- ============================================================
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

-- ============================================================
-- Migration: 005_create_career_profiles.sql
-- ============================================================
-- Migration 005: Create career_profiles table
-- Extended career intelligence per user — aspirations, target roles, embedding vector.
-- One-to-one with users in v1.0; architecture allows multiple profiles per user in future.

CREATE TABLE IF NOT EXISTS career_profiles (
    id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    "current_role"      text,
    target_roles        text[] NOT NULL DEFAULT '{}',
    industries          text[] NOT NULL DEFAULT '{}',
    aspirations_text    text,
    embedding           vector(1536),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE career_profiles IS 'Career intelligence profile — aspirations, target roles, vector embedding for semantic matching.';
COMMENT ON COLUMN career_profiles.embedding IS 'OpenAI text-embedding-3-small (1536 dims) of career profile for similarity search.';
COMMENT ON COLUMN career_profiles.target_roles IS 'Array of target role titles the user is pursuing.';
COMMENT ON COLUMN career_profiles.industries IS 'Array of target industry segments.';

-- ============================================================
-- Migration: 006_create_signals.sql
-- ============================================================
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

-- ============================================================
-- Migration: 007_create_opportunities.sql
-- ============================================================
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

-- ============================================================
-- Migration: 008_create_actions.sql
-- ============================================================
-- Migration 008: Create actions table
-- User task queue — generated by the Action Generator agent.
-- Each action links to an opportunity (and optionally a contact, company, signal).

CREATE TABLE IF NOT EXISTS actions (
    id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opportunity_id      uuid REFERENCES opportunities(id) ON DELETE SET NULL,
    company_id          uuid REFERENCES companies(id) ON DELETE SET NULL,
    contact_id          uuid REFERENCES contacts(id) ON DELETE SET NULL,
    title               text NOT NULL,
    description         text,
    type                text NOT NULL,              -- OUTREACH|FOLLOW_UP|RESEARCH|CALL
    priority            text NOT NULL DEFAULT 'MEDIUM', -- HIGH|MEDIUM|LOW
    status              text NOT NULL DEFAULT 'TODO',   -- TODO|IN_PROGRESS|DONE|SNOOZED
    due_date            timestamptz,
    source_signal_id    uuid REFERENCES signals(id) ON DELETE SET NULL,
    ai_draft_json       jsonb NOT NULL DEFAULT '{}',
    created_at          timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE actions IS 'Prioritized task queue for the user — generated by Action Generator agent.';
COMMENT ON COLUMN actions.type IS 'Action category: OUTREACH|FOLLOW_UP|RESEARCH|CALL';
COMMENT ON COLUMN actions.priority IS 'Priority band: HIGH|MEDIUM|LOW — computed from urgency × confidence × fit_score.';
COMMENT ON COLUMN actions.ai_draft_json IS 'Pre-computed AI draft payload (e.g., email draft) attached to this action.';

-- ============================================================
-- Migration: 009_create_outreach_emails.sql
-- ============================================================
-- Migration 009: Create outreach_emails table
-- Email drafts and send history — user must approve before any send.
-- Gmail message IDs stored for reply/open tracking.

CREATE TABLE IF NOT EXISTS outreach_emails (
    id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_id           uuid REFERENCES actions(id) ON DELETE SET NULL,
    contact_id          uuid REFERENCES contacts(id) ON DELETE SET NULL,
    subject             text,
    body                text,
    tone                text,
    draft_json          jsonb NOT NULL DEFAULT '{}',
    sent_at             timestamptz,
    gmail_message_id    text,
    opened_at           timestamptz,
    replied_at          timestamptz,
    reply_detected_at   timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE outreach_emails IS 'Email drafts and send history for outreach to contacts.';
COMMENT ON COLUMN outreach_emails.draft_json IS 'Full Email Drafter output (3 variants: Professional/Warm/Direct).';
COMMENT ON COLUMN outreach_emails.tone IS 'Selected tone variant: Professional|Warm|Direct.';
COMMENT ON COLUMN outreach_emails.gmail_message_id IS 'Gmail API message ID — used for reply/open tracking.';
COMMENT ON COLUMN outreach_emails.reply_detected_at IS 'When reply was first detected (for response-time metrics).';

-- ============================================================
-- Migration: 010_create_agent_runs.sql
-- ============================================================
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

-- ============================================================
-- Migration: 011_create_rls_policies.sql
-- ============================================================
-- Migration 011: Enable Row-Level Security and create access policies
-- ALL tables with user_id enforce RLS: users can only see/modify their own rows.
-- Companies and contacts are shared across users (no user_id column) — no RLS.
-- Run AFTER all table-creation migrations.

-- ── Enable RLS on all user-scoped tables ──────────────────────────────────────

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE career_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE outreach_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;

-- ── users ──────────────────────────────────────────────────────────────────────
-- Users can only read/update their own row. No self-delete.

CREATE POLICY users_select_own ON users
    FOR SELECT USING (id = auth.uid());

CREATE POLICY users_update_own ON users
    FOR UPDATE USING (id = auth.uid());

-- ── career_profiles ────────────────────────────────────────────────────────────

CREATE POLICY career_profiles_select_own ON career_profiles
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY career_profiles_insert_own ON career_profiles
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY career_profiles_update_own ON career_profiles
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY career_profiles_delete_own ON career_profiles
    FOR DELETE USING (user_id = auth.uid());

-- ── signals ────────────────────────────────────────────────────────────────────

CREATE POLICY signals_select_own ON signals
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY signals_insert_own ON signals
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY signals_update_own ON signals
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY signals_delete_own ON signals
    FOR DELETE USING (user_id = auth.uid());

-- ── opportunities ──────────────────────────────────────────────────────────────

CREATE POLICY opportunities_select_own ON opportunities
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY opportunities_insert_own ON opportunities
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY opportunities_update_own ON opportunities
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY opportunities_delete_own ON opportunities
    FOR DELETE USING (user_id = auth.uid());

-- ── actions ────────────────────────────────────────────────────────────────────

CREATE POLICY actions_select_own ON actions
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY actions_insert_own ON actions
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY actions_update_own ON actions
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY actions_delete_own ON actions
    FOR DELETE USING (user_id = auth.uid());

-- ── outreach_emails ────────────────────────────────────────────────────────────

CREATE POLICY outreach_emails_select_own ON outreach_emails
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY outreach_emails_insert_own ON outreach_emails
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY outreach_emails_update_own ON outreach_emails
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY outreach_emails_delete_own ON outreach_emails
    FOR DELETE USING (user_id = auth.uid());

-- ── agent_runs ─────────────────────────────────────────────────────────────────
-- Agent runs are append-only in production — no UPDATE/DELETE for audit integrity.

CREATE POLICY agent_runs_select_own ON agent_runs
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY agent_runs_insert_own ON agent_runs
    FOR INSERT WITH CHECK (user_id = auth.uid());

-- NOTE: No UPDATE or DELETE policies on agent_runs — audit trail is immutable.
-- Service role key bypasses RLS for backend writes — never expose service key to frontend.

-- ============================================================
-- Migration: 012_create_indexes.sql
-- ============================================================
-- Migration 012: Create performance indexes and pgvector IVFFlat indexes
-- Standard B-tree indexes for common filter/join patterns.
-- IVFFlat indexes for approximate nearest-neighbor vector search (pgvector).
-- Run AFTER all table-creation migrations.

-- ── users ──────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ── career_profiles ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_career_profiles_user_id ON career_profiles(user_id);

-- IVFFlat index for career profile embedding similarity search.
-- lists=100 is suitable for up to ~1M rows; tune lists = sqrt(row_count) at scale.
CREATE INDEX IF NOT EXISTS idx_career_profiles_embedding ON career_profiles
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── companies ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);
CREATE INDEX IF NOT EXISTS idx_companies_domain ON companies(domain);

-- ── contacts ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);

-- ── signals ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_signals_user_id ON signals(user_id);
CREATE INDEX IF NOT EXISTS idx_signals_company_id ON signals(company_id);
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(type);
CREATE INDEX IF NOT EXISTS idx_signals_signal_date ON signals(signal_date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_relevance_score ON signals(relevance_score);
-- dedup_hash already has a UNIQUE constraint (implicit index)

-- IVFFlat index for signal embedding similarity search.
CREATE INDEX IF NOT EXISTS idx_signals_embedding ON signals
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── opportunities ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_opportunities_user_id ON opportunities(user_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_company_id ON opportunities(company_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_confidence ON opportunities(confidence);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_fit_score ON opportunities(fit_score DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_created_at ON opportunities(created_at DESC);

-- ── actions ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_actions_user_id ON actions(user_id);
CREATE INDEX IF NOT EXISTS idx_actions_opportunity_id ON actions(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_priority ON actions(priority);
CREATE INDEX IF NOT EXISTS idx_actions_due_date ON actions(due_date);

-- ── outreach_emails ───────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_outreach_emails_user_id ON outreach_emails(user_id);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_action_id ON outreach_emails(action_id);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_contact_id ON outreach_emails(contact_id);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_sent_at ON outreach_emails(sent_at);

-- ── agent_runs ────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_name ON agent_runs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at DESC);

-- ============================================================
-- Migration: 014_add_real_postings.sql
-- ============================================================
-- Phase 14: Add real_postings JSONB column to opportunities table.
-- Null = not yet validated. [] = validated, no match. [{...}] = validated with postings.
ALTER TABLE opportunities
  ADD COLUMN IF NOT EXISTS real_postings JSONB DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_opportunities_real_postings_notnull
  ON opportunities ((real_postings IS NOT NULL))
  WHERE real_postings IS NOT NULL;

-- ============================================================
-- Migration 015: user_documents table (Phase 15)
-- ============================================================
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

-- ============================================================
-- Migration 016: extend career_profiles (Phase 15)
-- ============================================================
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

-- ============================================================
-- Migration 017: rename positioning_notes to approach_angle (Phase 15)
-- ============================================================
ALTER TABLE opportunities
  RENAME COLUMN positioning_notes TO approach_angle;
