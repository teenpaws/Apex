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
