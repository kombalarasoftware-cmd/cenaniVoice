-- Migration: Add dual-provider (OpenAI + Ultravox) support
-- Date: 2026-02-08
-- Description: Adds provider selection to agents, provider tracking to call_logs,
--              and batch tracking to campaigns.

BEGIN;

-- ============================================================
-- 1. Agent table: add provider selection and Ultravox agent ID
-- ============================================================
ALTER TABLE agents ADD COLUMN IF NOT EXISTS provider VARCHAR(20) DEFAULT 'openai';
ALTER TABLE agents ADD COLUMN IF NOT EXISTS ultravox_agent_id VARCHAR(255);

-- ============================================================
-- 2. CallLog table: add provider tracking and Ultravox call ID
-- ============================================================
ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS provider VARCHAR(20);
ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS ultravox_call_id VARCHAR(255);

-- Index for fast lookup by Ultravox call ID (used in webhooks)
CREATE INDEX IF NOT EXISTS ix_call_logs_ultravox_call_id
    ON call_logs (ultravox_call_id)
    WHERE ultravox_call_id IS NOT NULL;

-- ============================================================
-- 3. Campaign table: add Ultravox batch tracking
-- ============================================================
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS ultravox_batch_id VARCHAR(255);

-- ============================================================
-- 4. Update RealtimeModel enum type if stored as native enum
--    (Only needed if using PostgreSQL native enums; skip if
--     models are stored as VARCHAR)
-- ============================================================
-- If using native enum, uncomment and run:
-- ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'ULTRAVOX_V0_6';
-- ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'ULTRAVOX_V0_6_GEMMA3_27B';
-- ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'ULTRAVOX_V0_6_LLAMA3_3_70B';

COMMIT;
