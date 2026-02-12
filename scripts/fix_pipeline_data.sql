-- Fix pipeline agents: update provider and model_type to valid enum values
UPDATE agents SET provider = 'openai', model_type = 'GPT_REALTIME' WHERE provider = 'pipeline';
UPDATE agents SET model_type = 'GPT_REALTIME' WHERE model_type IN ('PIPELINE_CLOUD', 'pipeline-cloud', 'PIPELINE_QWEN_7B', 'PIPELINE_LLAMA_8B', 'PIPELINE_MISTRAL_7B', 'pipeline-qwen-7b', 'pipeline-llama-8b', 'pipeline-mistral-7b');

-- Verify fix
SELECT id, name, provider, model_type FROM agents;

-- Remove pipeline enum values from realtimemodel
DELETE FROM pg_enum WHERE enumlabel IN ('PIPELINE_CLOUD', 'pipeline-cloud', 'PIPELINE_QWEN_7B', 'PIPELINE_LLAMA_8B', 'PIPELINE_MISTRAL_7B', 'pipeline-qwen-7b', 'pipeline-llama-8b', 'pipeline-mistral-7b')
  AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'realtimemodel');

-- Verify enum cleanup
SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'realtimemodel');
