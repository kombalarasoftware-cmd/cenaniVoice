import asyncio
import httpx
import os
import json

api_key = os.environ.get('ULTRAVOX_API_KEY', '')
print(f'API Key exists: {bool(api_key)}')

async def fetch():
    headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}
    async with httpx.AsyncClient(base_url='https://api.ultravox.ai/api', headers=headers, timeout=30) as client:
        # Turkish voices
        r = await client.get('/voices', params={'primaryLanguage': 'tr', 'pageSize': 50})
        voices_tr = r.json()
        print('=== TURKISH VOICES ===')
        for v in voices_tr.get('results', []):
            name = v.get('name', '')
            vid = v.get('voiceId', '')
            prov = v.get('provider', '')
            lang = v.get('languageLabel', '')
            billing = v.get('billingStyle', '')
            desc = v.get('description', '')
            primary = v.get('primaryLanguage', '')
            print(f'  {name} | id={vid[:12]}... | provider={prov} | lang={primary} | label={lang} | billing={billing}')
            if desc:
                print(f'    desc: {desc[:100]}')
        print(f'Total TR voices: {voices_tr.get("total", 0)}')
        
        # All included voices
        r2 = await client.get('/voices', params={'pageSize': 200, 'billingStyle': 'VOICE_BILLING_STYLE_INCLUDED'})
        voices_all = r2.json()
        print(f'\n=== ALL INCLUDED VOICES (total: {voices_all.get("total", 0)}) ===')
        for v in voices_all.get('results', []):
            name = v.get('name', '')
            prov = v.get('provider', '')
            primary = v.get('primaryLanguage', '')
            lang = v.get('languageLabel', '')
            print(f'  {name} | provider={prov} | lang={primary} | label={lang}')

        # Check available models
        print('\n=== CHECKING MODELS ===')
        # Try creating a call with different models to see what's available
        models_to_test = [
            'ultravox-v0.7',
            'ultravox-v0.6',
            'ultravox-v0.6-gemma3-27b',
            'ultravox-v0.6-llama3.3-70b',
        ]
        for model in models_to_test:
            print(f'  Model: {model}')

asyncio.run(fetch())
