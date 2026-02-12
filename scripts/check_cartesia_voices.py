"""Fetch Cartesia voices from API"""
import httpx
import os
import json

key = os.environ.get("CARTESIA_API_KEY", "")
print(f"API key: {key[:10]}...")

r = httpx.get(
    "https://api.cartesia.ai/voices",
    headers={
        "X-API-Key": key,
        "Cartesia-Version": "2025-04-16",
    },
    timeout=30.0
)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    print(f"Type: {type(data)}")
    print(f"Raw: {json.dumps(data, indent=2, ensure_ascii=False)[:3000]}")
else:
    print(f"Error: {r.text[:500]}")
