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
