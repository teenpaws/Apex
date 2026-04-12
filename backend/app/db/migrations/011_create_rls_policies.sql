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
