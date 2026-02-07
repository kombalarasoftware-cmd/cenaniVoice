-- ========================================
-- Survey System Migration Script
-- ========================================
-- Bu script anket sistemini ekler:
-- 1. agents tablosuna survey_config kolonu
-- 2. survey_responses tablosu
-- ========================================

-- 1. Agents tablosuna survey_config kolonu ekle
ALTER TABLE agents 
ADD COLUMN IF NOT EXISTS survey_config JSONB DEFAULT '{}';

-- 2. Survey responses tablosu oluştur
CREATE TABLE IF NOT EXISTS survey_responses (
    id SERIAL PRIMARY KEY,
    
    -- İlişkiler
    call_id INTEGER REFERENCES call_logs(id) ON DELETE SET NULL,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    
    -- Yanıtlayıcı bilgileri
    respondent_phone VARCHAR(50),
    respondent_name VARCHAR(255),
    
    -- Anket durumu
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'abandoned')),
    
    -- Cevaplar (JSON array)
    -- Format: [{"question_id": "q1", "question_text": "...", "answer": "...", "answer_value": 5}]
    answers JSONB DEFAULT '[]',
    
    -- İlerleme takibi
    current_question_id VARCHAR(50),
    questions_answered INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    
    -- Süre metrikleri
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- İndeksler
CREATE INDEX IF NOT EXISTS idx_survey_responses_call_id ON survey_responses(call_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_agent_id ON survey_responses(agent_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_campaign_id ON survey_responses(campaign_id);
CREATE INDEX IF NOT EXISTS idx_survey_responses_respondent_phone ON survey_responses(respondent_phone);
CREATE INDEX IF NOT EXISTS idx_survey_responses_status ON survey_responses(status);
CREATE INDEX IF NOT EXISTS idx_survey_responses_created_at ON survey_responses(created_at);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_survey_responses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_survey_responses_updated_at ON survey_responses;
CREATE TRIGGER trigger_survey_responses_updated_at
    BEFORE UPDATE ON survey_responses
    FOR EACH ROW
    EXECUTE FUNCTION update_survey_responses_updated_at();

-- ========================================
-- Örnek Anket Yapılandırması (Referans)
-- ========================================
/*
UPDATE agents SET survey_config = '{
    "enabled": true,
    "questions": [
        {
            "id": "q1",
            "type": "yes_no",
            "text": "Hizmetimizden memnun musunuz?",
            "required": true,
            "next_on_yes": "q2a",
            "next_on_no": "q2b"
        },
        {
            "id": "q2a",
            "type": "rating",
            "text": "1 ile 10 arasında puan verir misiniz?",
            "required": true,
            "min_value": 1,
            "max_value": 10,
            "min_label": "Çok kötü",
            "max_label": "Mükemmel",
            "next": null
        },
        {
            "id": "q2b",
            "type": "multiple_choice",
            "text": "Hangi konuları geliştirebiliriz?",
            "required": true,
            "options": ["Hız", "Fiyat", "Kalite", "Müşteri Hizmetleri"],
            "allow_multiple": true,
            "next": "q3"
        },
        {
            "id": "q3",
            "type": "open_ended",
            "text": "Başka eklemek istediğiniz bir şey var mı?",
            "required": false,
            "max_length": 500,
            "next": null
        }
    ],
    "start_question": "q1",
    "completion_message": "Değerli geri bildiriminiz için teşekkür ederiz!",
    "abort_message": "Anket iptal edildi. Yardımcı olabildiysem ne mutlu.",
    "allow_skip": false,
    "show_progress": true
}'::jsonb WHERE id = 1;
*/

-- Doğrulama
SELECT 'survey_config column added to agents' AS status 
WHERE EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'agents' AND column_name = 'survey_config'
);

SELECT 'survey_responses table created' AS status 
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_name = 'survey_responses'
);
