#!/usr/bin/env python3
"""Test outbound call via API"""
import json
import urllib.request
import sys

BASE = "https://one.speakmaxi.com/api/v1"

# Login
login_data = json.dumps({"email": "admin@speakmaxi.com", "password": "Speakmaxi2026!"}).encode()
req = urllib.request.Request(f"{BASE}/auth/login", data=login_data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
token = json.loads(resp.read())["access_token"]
print(f"Got token: {token[:20]}...")

# Make outbound call
call_data = json.dumps({
    "phone_number": "4921666846161",
    "agent_id": "3",
    "caller_id": "491632086421"
}).encode()

req2 = urllib.request.Request(
    f"{BASE}/calls/outbound",
    data=call_data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
)

try:
    resp2 = urllib.request.urlopen(req2)
    result = json.loads(resp2.read())
    print(f"Call result: {json.dumps(result, indent=2)}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error {e.code}: {body}")
