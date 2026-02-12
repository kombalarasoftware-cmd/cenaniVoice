"""Fetch ALL Cartesia voices with pagination - try different cursor params."""
import os
import json
import urllib.request
import time

API_KEY = os.environ.get("CARTESIA_API_KEY", "sk_car_9146rFdFofoTKTeNw3UR5D")

all_voices = []
cursor = None
page = 0

while True:
    page += 1
    url = "https://api.cartesia.ai/voices"
    params = []
    if cursor:
        params.append(f"starting_after={cursor}")
    # Try with limit
    params.append("limit=100")
    if params:
        url += "?" + "&".join(params)
    
    print(f"Page {page}: GET {url}")
    
    req = urllib.request.Request(url, headers={
        "X-API-Key": API_KEY,
        "Cartesia-Version": "2024-06-10",
        "Accept": "application/json",
    })
    
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            data = json.loads(raw)
    except Exception as e:
        print(f"Error on page {page}: {e}")
        # If 403 on pagination, try alternative cursor param
        if cursor and "403" in str(e):
            url2 = f"https://api.cartesia.ai/voices?cursor={cursor}&limit=100"
            print(f"  Retrying with cursor param: {url2}")
            req2 = urllib.request.Request(url2, headers={
                "X-API-Key": API_KEY,
                "Cartesia-Version": "2024-06-10",
                "Accept": "application/json",
            })
            try:
                with urllib.request.urlopen(req2) as resp2:
                    raw = resp2.read().decode()
                    data = json.loads(raw)
            except Exception as e2:
                print(f"  Also failed with cursor: {e2}")
                # Try with page number
                url3 = f"https://api.cartesia.ai/voices?page={page}&limit=100"
                print(f"  Retrying with page param: {url3}")
                req3 = urllib.request.Request(url3, headers={
                    "X-API-Key": API_KEY,
                    "Cartesia-Version": "2024-06-10",
                    "Accept": "application/json",
                })
                try:
                    with urllib.request.urlopen(req3) as resp3:
                        raw = resp3.read().decode()
                        data = json.loads(raw)
                except Exception as e3:
                    print(f"  All pagination attempts failed: {e3}")
                    break
        else:
            break
    
    voices = data.get("data", [])
    all_voices.extend(voices)
    print(f"  Got {len(voices)} voices (total: {len(all_voices)})")
    
    if not data.get("has_more"):
        print("  No more pages.")
        break
    cursor = data.get("next_page")
    if not cursor:
        print("  No cursor returned.")
        break
    
    time.sleep(0.5)  # Small delay

# Group by language
by_lang = {}
for v in all_voices:
    lang = v.get("language", "unknown")
    if lang not in by_lang:
        by_lang[lang] = []
    by_lang[lang].append({
        "id": v["id"],
        "name": v["name"],
        "gender": v.get("gender", "unknown"),
        "description": v.get("description", ""),
    })

print(f"\n{'='*80}")
print(f"TOTAL VOICES: {len(all_voices)}")
print(f"LANGUAGES: {sorted(by_lang.keys())}")
print(f"{'='*80}\n")

for lang in sorted(by_lang.keys()):
    voices = by_lang[lang]
    print(f"\n--- {lang.upper()} ({len(voices)} voices) ---")
    for v in voices:
        desc = v['description'][:55] if v['description'] else ''
        print(f"  {v['id']}  |  {v['name']:40s}  |  {v['gender']:10s}  |  {desc}")
