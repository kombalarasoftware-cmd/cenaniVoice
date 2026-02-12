#!/bin/bash
# Add pipeline enum values to PostgreSQL

echo "=== Current realtimemodel enum values ==="
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "SELECT enum_range(NULL::realtimemodel);"

echo ""
echo "=== Adding pipeline enum values ==="
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'pipeline-qwen-7b';"
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'pipeline-llama-8b';"
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "ALTER TYPE realtimemodel ADD VALUE IF NOT EXISTS 'pipeline-mistral-7b';"
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "ALTER TYPE aiprovider ADD VALUE IF NOT EXISTS 'pipeline';"

echo ""
echo "=== Updated realtimemodel enum values ==="
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "SELECT enum_range(NULL::realtimemodel);"

echo ""
echo "=== Updated aiprovider enum values ==="
docker exec voiceai-postgres-1 psql -U postgres -d voiceai -c "SELECT enum_range(NULL::aiprovider);"
