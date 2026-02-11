#!/usr/bin/env python3
"""Test login API endpoint"""
import urllib.request
import json

data = json.dumps({"email": "admin@speakmaxi.com", "password": "Speakmaxi2026!"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/v1/auth/login",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        print(f"STATUS: {resp.status}")
        print(f"BODY: {resp.read().decode()[:300]}")
except urllib.error.HTTPError as e:
    print(f"STATUS: {e.code}")
    print(f"BODY: {e.read().decode()[:300]}")
except Exception as e:
    print(f"ERROR: {e}")
