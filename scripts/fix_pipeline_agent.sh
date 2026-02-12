#!/bin/bash
# Fix Pipeline Test Agent - update model and voice via API

API="https://one.speakmaxi.com/api/v1"

# Login
LOGIN_RESP=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"cmutlu2006@hotmail.com","password":"Speakmaxi2026!"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "Login failed: $LOGIN_RESP"
  exit 1
fi
echo "Token: ${TOKEN:0:20}..."

# Update Pipeline Agent (ID=5) with correct voice_settings
echo ""
echo "=== Updating Pipeline Agent ==="
UPDATE_RESP=$(curl -s -X PUT "$API/agents/5" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "voice_settings": {
      "model_type": "pipeline-qwen-7b",
      "voice": "tr_TR-dfki-medium",
      "language": "tr",
      "speech_speed": 1.0
    },
    "prompt": {
      "role": "You are a friendly Turkish-speaking test assistant for the Pipeline provider.",
      "personality": "Warm, helpful, concise. Always respond in Turkish.",
      "task": "Greet the caller, ask how you can help them, and have a brief test conversation.",
      "rules": "Keep responses under 2 sentences. Be natural and conversational."
    },
    "greeting_settings": {
      "first_speaker": "agent",
      "greeting_message": "Merhaba, ben yapay zeka asistanınız. Size nasıl yardımcı olabilirim?"
    }
  }')

echo "Update response: $UPDATE_RESP" | head -5

# Verify agent
echo ""
echo "=== Verifying Agent ==="
AGENT=$(curl -s "$API/agents/5" -H "Authorization: Bearer $TOKEN")
echo "$AGENT" | python3 -c "
import sys, json
a = json.load(sys.stdin)
print(f'  Name: {a.get(\"name\")}')
print(f'  Provider: {a.get(\"provider\")}')
print(f'  Model: {a.get(\"model_type\", a.get(\"voice_settings\",{}).get(\"model_type\",\"?\"))}')
print(f'  Voice: {a.get(\"voice\")}')
print(f'  Language: {a.get(\"language\")}')
print(f'  Greeting: {a.get(\"greeting_message\", \"?\")[:50]}')
"

echo ""
echo "=== Pipeline Status ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'pipeline|piper|ollama'
docker exec voiceai-ollama-1 ollama list

echo ""
echo "Pipeline agent ID=5 ready for test call!"
