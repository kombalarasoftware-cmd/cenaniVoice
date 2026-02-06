-- VoiceAI Platform Database Initialization
-- This script runs automatically when PostgreSQL container starts

-- Create database if not exists (already created by POSTGRES_DB env var)
-- Just ensure extensions are enabled

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE voiceai TO postgres;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'VoiceAI database initialized successfully!';
END $$;
