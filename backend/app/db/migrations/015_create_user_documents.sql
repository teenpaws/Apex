-- Migration 015: Create user_documents table (Phase 15)
-- Stores resume and cover letters uploaded by users.
-- extracted_text: local extraction (pdfplumber/python-docx), never sent to storage.
-- staging_json: ProfileExtractor output pending user approval.

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

COMMENT ON TABLE user_documents IS 'User-uploaded documents (resume, cover letters) with extracted text and staging area for profile extraction output.';
COMMENT ON COLUMN user_documents.staging_json IS 'ProfileExtractor output awaiting user approval — written to career_profiles on approve.';
