"""Fetch ALL Cartesia voices - with proper User-Agent header."""
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
        "User-Agent": "VoiceAI/1.0",
    })
    
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode()
        data = json.loads(raw)
    
    # Handle both list and dict response formats
    if isinstance(data, list):
        voices = data
        has_more = False
        next_page = None
    else:
        voices = data.get("data", [])
        has_more = data.get("has_more", False)
        next_page = data.get("next_page")
    
    all_voices.extend(voices)
    print(f"Page {page}: fetched {len(voices)} voices (total: {len(all_voices)}), has_more={has_more}")
    
    if not has_more:
        break
    cursor = next_page
    if not cursor:
        break

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

# Also dump JSON for programmatic use
with open("/tmp/cartesia_voices.json" if os.name != "nt" else "cartesia_voices.json", "w") as f:
    json.dump(by_lang, f, indent=2)
    print(f"\nSaved to {f.name}")
