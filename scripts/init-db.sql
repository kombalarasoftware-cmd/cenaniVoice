-- VoiceAI Platform Database Initialization
-- This script runs automatically when PostgreSQL container starts.
-- It ONLY handles extensions and privileges.
-- All table schemas are managed by Alembic migrations.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE voiceai TO postgres;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'VoiceAI database extensions initialized. Run "alembic upgrade head" to create tables.';
END $$;
