"""Quick test: Login and make outbound call to verify xAI Grok provider."""
import requests
import json
import sys

BASE = "https://one.speakmaxi.com"

# Login
login_resp = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "cmutlu2006@hotmail.com",
    "password": "Speakmaxi2026!"
})
if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.status_code} {login_resp.text[:200]}")
    sys.exit(1)

token = login_resp.json().get("access_token", "")
print(f"Login OK, token: {token[:30]}...")

# Make outbound call
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
call_resp = requests.post(f"{BASE}/api/v1/calls/outbound", headers=headers, json={
    "phone_number": "4921666846161",
    "agent_id": "3",
    "caller_id": "491632086421"
})
print(f"Call response: {call_resp.status_code}")
print(json.dumps(call_resp.json(), indent=2, ensure_ascii=False))
