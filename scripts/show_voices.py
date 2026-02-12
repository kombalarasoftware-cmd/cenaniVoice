import json

with open("cartesia_voices.json") as f:
    data = json.load(f)

for lang in ["tr", "en", "de", "fr", "es", "it", "ar", "ru", "ja", "ko", "zh", "pt", "nl", "pl", "hi", "sv"]:
    if lang in data:
        print(f"\n=== {lang.upper()} ({len(data[lang])} voices) ===")
        for v in data[lang]:
            print(f"  {v['id']}  |  {v['name']:40s}  |  {v['gender']}")
