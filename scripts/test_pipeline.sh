#!/bin/bash
# Test Pipeline Provider - Create agent and make test call

API="https://one.speakmaxi.com/api/v1"

# Login
echo "=== Login ==="
LOGIN_RESP=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"cmutlu2006@hotmail.com","password":"Speakmaxi2026!"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "Login failed: $LOGIN_RESP"
  exit 1
fi
echo "Token acquired: ${TOKEN:0:20}..."

# Create Pipeline Agent
echo ""
echo "=== Creating Pipeline Agent ==="
AGENT_RESP=$(curl -s -X POST "$API/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Pipeline Test Agent",
    "provider": "pipeline",
    "model": "pipeline-qwen-7b",
    "voice": "tr_TR-dfki-medium",
    "language": "tr",
    "system_prompt": "You are a friendly Turkish-speaking assistant. Greet the caller and ask how you can help them today. Keep responses short and natural.",
    "first_message": "Merhaba, ben yapay zeka asistanınız. Size nasıl yardımcı olabilirim?",
    "temperature": 0.7
  }')

AGENT_ID=$(echo "$AGENT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)

if [ -z "$AGENT_ID" ]; then
  echo "Agent creation failed: $AGENT_RESP"
  exit 1
fi
echo "Agent created: ID=$AGENT_ID"

# List agents to verify
echo ""
echo "=== Agents List ==="
curl -s "$API/agents" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
agents = json.load(sys.stdin)
if isinstance(agents, list):
    for a in agents:
        print(f\"  - {a.get('name','?')}: provider={a.get('provider','?')}, model={a.get('model','?')}, voice={a.get('voice','?')}\")
elif isinstance(agents, dict) and 'items' in agents:
    for a in agents['items']:
        print(f\"  - {a.get('name','?')}: provider={a.get('provider','?')}, model={a.get('model','?')}, voice={a.get('voice','?')}\")
else:
    print(agents)
"

# Check pipeline-bridge health
echo ""
echo "=== Pipeline Bridge Status ==="
docker logs voiceai-pipeline-bridge-1 --tail=5 2>&1

echo ""
echo "=== Ollama Model Check ==="
docker exec voiceai-ollama-1 ollama list 2>&1

echo ""
echo "=== All Pipeline Containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'pipeline|piper|ollama'

echo ""
echo "Pipeline agent ready! You can now make a test call from the UI."
echo "Agent ID: $AGENT_ID"
