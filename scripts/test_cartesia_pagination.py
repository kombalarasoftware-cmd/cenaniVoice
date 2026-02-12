"""Fetch ALL Cartesia voices - test different API versions and params."""
import os
import json
import urllib.request
import time

API_KEY = os.environ.get("CARTESIA_API_KEY", "sk_car_9146rFdFofoTKTeNw3UR5D")

# Test 1: No params, original version
print("=== Test 1: No params, version 2024-06-10 ===")
req = urllib.request.Request("https://api.cartesia.ai/voices", headers={
    "X-API-Key": API_KEY,
    "Cartesia-Version": "2024-06-10",
})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    voices = data.get("data", [])
    cursor = data.get("next_page")
    has_more = data.get("has_more")
    print(f"Got {len(voices)} voices, has_more={has_more}, cursor={cursor}")

# Test 2: With starting_after, same version
if cursor and has_more:
    time.sleep(1)
    print(f"\n=== Test 2: starting_after={cursor}, version 2024-06-10 ===")
    try:
        req2 = urllib.request.Request(f"https://api.cartesia.ai/voices?starting_after={cursor}", headers={
            "X-API-Key": API_KEY,
            "Cartesia-Version": "2024-06-10",
        })
        with urllib.request.urlopen(req2) as resp2:
            data2 = json.loads(resp2.read().decode())
            print(f"Got {len(data2.get('data', []))} voices")
    except Exception as e:
        print(f"Error: {e}")

# Test 3: Try newer API version
if cursor and has_more:
    time.sleep(1)
    print(f"\n=== Test 3: starting_after={cursor}, version 2025-04-16 ===")
    try:
        req3 = urllib.request.Request(f"https://api.cartesia.ai/voices?starting_after={cursor}", headers={
            "X-API-Key": API_KEY,
            "Cartesia-Version": "2025-04-16",
        })
        with urllib.request.urlopen(req3) as resp3:
            data3 = json.loads(resp3.read().decode())
            print(f"Got {len(data3.get('data', []))} voices")
    except Exception as e:
        print(f"Error: {e}")

# Test 4: Try without version header
if cursor and has_more:
    time.sleep(1)
    print(f"\n=== Test 4: starting_after={cursor}, no version header ===")
    try:
        req4 = urllib.request.Request(f"https://api.cartesia.ai/voices?starting_after={cursor}", headers={
            "X-API-Key": API_KEY,
        })
        with urllib.request.urlopen(req4) as resp4:
            data4 = json.loads(resp4.read().decode())
            print(f"Got {len(data4.get('data', []))} voices")
    except Exception as e:
        print(f"Error: {e}")

# Test 5: Try different endpoint patterns
if cursor and has_more:
    time.sleep(1)
    for param_name in ["cursor", "after", "offset"]:
        print(f"\n=== Test 5: {param_name}={cursor} ===")
        try:
            req5 = urllib.request.Request(f"https://api.cartesia.ai/voices?{param_name}={cursor}", headers={
                "X-API-Key": API_KEY,
                "Cartesia-Version": "2024-06-10",
            })
            with urllib.request.urlopen(req5) as resp5:
                data5 = json.loads(resp5.read().decode())
                print(f"Got {len(data5.get('data', []))} voices")
                break
        except Exception as e:
            print(f"Error: {e}")
