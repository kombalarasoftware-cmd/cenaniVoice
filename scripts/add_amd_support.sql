-- AMD (Answering Machine Detection) support
-- Adds amd_status and amd_cause columns to call_logs table

ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS amd_status VARCHAR(20);
ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS amd_cause VARCHAR(100);

-- Index for filtering machine-detected calls
CREATE INDEX IF NOT EXISTS ix_call_logs_amd_status ON call_logs(amd_status);
