#!/bin/bash
# Fix pipeline enum values - need to use NAME format (uppercase) not value format

echo "=== Current enum values ==="
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "SELECT enum_range(NULL::realtimemodel);"

echo ""
echo "=== Adding pipeline enum values (NAME format) ==="
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'PIPELINE_QWEN_7B';"
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'PIPELINE_LLAMA_8B';"
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'PIPELINE_MISTRAL_7B';"

echo ""
echo "=== Updated enum values ==="
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "SELECT enum_range(NULL::realtimemodel);"
