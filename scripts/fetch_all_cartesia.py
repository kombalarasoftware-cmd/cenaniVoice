"""Fetch ALL Cartesia voices with pagination and group by language."""
import os
import json
import urllib.request

API_KEY = os.environ.get("CARTESIA_API_KEY", "sk_car_9146rFdFofoTKTeNw3UR5D")

all_voices = []
cursor = None
page = 0

while True:
    page += 1
    url = "https://api.cartesia.ai/voices"
    if cursor:
        url += f"?starting_after={cursor}"
    
    req = urllib.request.Request(url, headers={
        "X-API-Key": API_KEY,
        "Cartesia-Version": "2024-06-10",
    })
    
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    
    voices = data.get("data", [])
    all_voices.extend(voices)
    print(f"Page {page}: fetched {len(voices)} voices (total: {len(all_voices)})")
    
    if not data.get("has_more"):
        break
    cursor = data.get("next_page")

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
        print(f"  {v['id']}  |  {v['name']:40s}  |  {v['gender']:10s}  |  {v['description'][:60]}")
