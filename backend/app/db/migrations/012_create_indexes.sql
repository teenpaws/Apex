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
