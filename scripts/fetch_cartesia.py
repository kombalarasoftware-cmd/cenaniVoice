"""Fetch ALL Cartesia voices from API and display them"""
import httpx
import os
import json

key = os.environ.get("CARTESIA_API_KEY", "")
print(f"API key: {key[:10]}...")

# Try /voices endpoint
r = httpx.get(
    "https://api.cartesia.ai/voices",
    headers={
        "X-API-Key": key,
        "Cartesia-Version": "2025-04-16",
    },
    timeout=30.0
)
print(f"Status: {r.status_code}")
print(f"Type: {type(r.json())}")
print(f"Raw response (first 5000 chars):")
print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:5000])
