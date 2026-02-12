-- Fix Agent 3: Dr. Ayşe - set Turkish Cartesia voice and LLM model
UPDATE agents 
SET tts_voice = 'leyla', 
    llm_model = 'llama-3.3-70b-versatile' 
WHERE id = 3;

-- Fix Agent 4: Müşteri Memnuniyeti - set Turkish Cartesia voice
UPDATE agents 
SET tts_voice = 'leyla' 
WHERE id = 4;
