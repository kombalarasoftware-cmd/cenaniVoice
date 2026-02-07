-- Smart Features Migration
-- Run this SQL to add smart_features column to agents table

-- Add smart_features column to agents if not exists
ALTER TABLE agents ADD COLUMN IF NOT EXISTS smart_features JSON DEFAULT '{}';

-- Add index for querying agents with specific features enabled
CREATE INDEX IF NOT EXISTS idx_agents_smart_features ON agents USING gin(smart_features);

-- Comments
COMMENT ON COLUMN agents.smart_features IS 'Akıllı özellikler - lead yakalama, çağrı etiketleri, geri arama ayarları (JSON)';
