-- Migration 005: Create career_profiles table
-- Extended career intelligence per user — aspirations, target roles, embedding vector.
-- One-to-one with users in v1.0; architecture allows multiple profiles per user in future.

CREATE TABLE IF NOT EXISTS career_profiles (
    id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_role        text,
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
