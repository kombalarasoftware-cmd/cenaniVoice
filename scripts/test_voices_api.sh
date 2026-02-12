#!/bin/bash
# Test pipeline voices API
set -e

LOGIN_RESP=$(curl -s -X POST "https://one.speakmaxi.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${VOICEAI_EMAIL:?Please set VOICEAI_EMAIL}\",\"password\":\"${VOICEAI_PASSWORD:?Please set VOICEAI_PASSWORD}\"}")

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "=== Pipeline Voices ==="
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://one.speakmaxi.com/api/v1/agents/voices/list?provider=pipeline" \
  | python3 -m json.tool

echo ""
echo "=== Voice Count ==="
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://one.speakmaxi.com/api/v1/agents/voices/list?provider=pipeline" \
  | python3 -c "import sys,json; data=json.load(sys.stdin); print(f'Total: {len(data)} voices')"
