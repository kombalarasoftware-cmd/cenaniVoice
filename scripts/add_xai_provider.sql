-- Add xAI provider and Grok model to PostgreSQL enums
-- Run: docker exec -i voiceai-postgres psql -U postgres -d voiceai < scripts/add_xai_provider.sql

-- Add 'xai' to aiprovider enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'xai' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'aiprovider')) THEN
        ALTER TYPE aiprovider ADD VALUE 'xai';
    END IF;
END
$$;

-- Add 'grok-2-realtime' to realtimemodel enum (the DB value)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'grok-2-realtime' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'realtimemodel')) THEN
        ALTER TYPE realtimemodel ADD VALUE 'grok-2-realtime';
    END IF;
END
$$;

-- Add 'XAI_GROK' to realtimemodel enum (SQLAlchemy uses enum NAME, not value)
ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'XAI_GROK';

-- Verify
SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'aiprovider') ORDER BY enumsortorder;
SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'realtimemodel') ORDER BY enumsortorder;
