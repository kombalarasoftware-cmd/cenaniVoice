#!/bin/bash
# Make a test call via Pipeline provider

API="https://one.speakmaxi.com/api/v1"
TEST_PHONE="4921666846161"  # Test number

# Login
LOGIN_RESP=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"cmutlu2006@hotmail.com","password":"Speakmaxi2026!"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "Login failed: $LOGIN_RESP"
  exit 1
fi
echo "Logged in successfully"

# Make outbound call with Pipeline agent (ID=5)
echo ""
echo "=== Initiating Pipeline Test Call ==="
CALL_RESP=$(curl -s -X POST "$API/calls/outbound" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"phone_number\": \"$TEST_PHONE\",
    \"caller_id\": \"491632086421\",
    \"agent_id\": \"5\",
    \"customer_name\": \"Test User\"
  }")

echo "Call response: $CALL_RESP"

# Parse result
echo "$CALL_RESP" | python3 -c "
import sys, json
r = json.load(sys.stdin)
if r.get('success'):
    print(f'  Call ID: {r.get(\"call_id\",\"?\")}')
    print(f'  Channel: {r.get(\"channel_id\",\"?\")}')
    print(f'  DB ID: {r.get(\"db_call_id\",\"?\")}')
    print(f'  Message: {r.get(\"message\",\"?\")}')
else:
    print(f'  FAILED: {r.get(\"message\",r)}')
" 2>/dev/null

echo ""
echo "=== Pipeline Bridge Logs (last 5 lines) ==="
docker logs voiceai-pipeline-bridge-1 --tail=5 2>&1

echo ""
echo "=== Asterisk Active Channels ==="
docker exec voiceai-asterisk-1 asterisk -rx 'core show channels' 2>&1 | tail -5
