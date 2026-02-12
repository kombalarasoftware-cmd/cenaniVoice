"""
Cloud TTS (Text-to-Speech) Providers
=======================================
Supported providers:
  - Cartesia (Sonic-3, ultra-low latency, 42 languages)
  - OpenAI (tts-1, tts-1-hd, gpt-4o-mini-tts)
  - Deepgram (Aura-2)

All providers return raw PCM16 audio at the requested sample rate.
"""

import time
import logging
from typing import Optional

import httpx

logger = logging.getLogger("pipeline-bridge")


# ============================================================================
# CARTESIA TTS
# ============================================================================

# Cartesia voices — verified from API (all IDs validated 2025-02)
CARTESIA_VOICES = {
    # ── Turkish ──────────────────────────────────────────────────────────
    "leyla": {"id": "fa7bfcdc-603c-4bf1-a600-a371400d2f8c", "label": "Leyla (Female, TR)", "lang": "tr"},
    "aylin": {"id": "bb2347fe-69e9-4810-873f-ffd759fe8420", "label": "Aylin (Female, TR)", "lang": "tr"},
    "azra": {"id": "0f95596c-09c4-4418-99fe-5c107e0713c0", "label": "Azra (Female, TR)", "lang": "tr"},
    "zehra": {"id": "91e91d74-8eb4-43cd-97d3-7466c21db00d", "label": "Zehra (Female, TR)", "lang": "tr"},
    "emre": {"id": "39f753ef-b0eb-41cd-aa53-2f3c284f948f", "label": "Emre (Male, TR)", "lang": "tr"},
    "taylan": {"id": "c1cfee3d-532d-47f8-8dd2-8e5b2b66bf1d", "label": "Taylan (Male, TR)", "lang": "tr"},
    "murat": {"id": "5a31e4fb-f823-4359-aa91-82c0ae9a991c", "label": "Murat (Male, TR)", "lang": "tr"},
    # Legacy aliases
    "turkish-female": {"id": "0f95596c-09c4-4418-99fe-5c107e0713c0", "label": "Azra (Female, TR)", "lang": "tr"},
    "turkish-male": {"id": "39f753ef-b0eb-41cd-aa53-2f3c284f948f", "label": "Emre (Male, TR)", "lang": "tr"},

    # ── English ──────────────────────────────────────────────────────────
    "katie": {"id": "f786b574-daa5-4673-aa0c-cbe3e8534c02", "label": "Katie (Female, EN)", "lang": "en"},
    "tessa": {"id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b", "label": "Tessa (Female, EN)", "lang": "en"},
    "sarah": {"id": "694f9389-aac1-45b6-b726-9d9369183238", "label": "Sarah (Female, EN)", "lang": "en"},
    "mia": {"id": "1d3ba41a-96e6-44ad-aabb-9817c56caa68", "label": "Mia (Female, EN)", "lang": "en"},
    "ellen": {"id": "5c9e800f-2a92-4720-969b-99c4ab8fbc87", "label": "Ellen (Female, EN)", "lang": "en"},
    "samantha": {"id": "f4e8781b-a420-4080-81cf-576331238efa", "label": "Samantha (Female, EN)", "lang": "en"},
    "emma": {"id": "f6ff7c0c-e396-40a9-a70b-f7607edb6937", "label": "Emma (Female, EN)", "lang": "en"},
    "sophie": {"id": "bf0a246a-8642-498a-9950-80c35e9276b5", "label": "Sophie (Female, EN)", "lang": "en"},
    "kiefer": {"id": "228fca29-3a0a-435c-8728-5cb483251068", "label": "Kiefer (Male, EN)", "lang": "en"},
    "kyle": {"id": "c961b81c-a935-4c17-bfb3-ba2239de8c2f", "label": "Kyle (Male, EN)", "lang": "en"},
    "blake": {"id": "a167e0f3-df7e-4d52-a9c3-f949145efdab", "label": "Blake (Male, EN)", "lang": "en"},
    "joey": {"id": "34575e71-908f-4ab6-ab54-b08c95d6597d", "label": "Joey (Male, EN)", "lang": "en"},
    "liam": {"id": "41f3c367-e0a8-4a85-89e0-c27bae9c9b6d", "label": "Liam (Male, EN)", "lang": "en"},
    "barry": {"id": "13524ffb-a918-499a-ae97-c98c7c4408c4", "label": "Barry (Male, EN)", "lang": "en"},

    # ── German ───────────────────────────────────────────────────────────
    "alina": {"id": "38aabb6a-f52b-4fb0-a3d1-988518f4dc06", "label": "Alina (Female, DE)", "lang": "de"},
    "viktoria": {"id": "b9de4a89-2257-424b-94c2-db18ba68c81a", "label": "Viktoria (Female, DE)", "lang": "de"},
    "karin": {"id": "3f4ade23-6eb4-4279-ab05-6a144947c4d5", "label": "Karin (Female, DE)", "lang": "de"},
    "lea": {"id": "1ade29fc-6b82-4607-9e70-361720139b12", "label": "Lea (Female, DE)", "lang": "de"},
    "lena": {"id": "4ab1ff51-476d-42bb-8019-4d315f7c0c05", "label": "Lena (Female, DE)", "lang": "de"},
    "lorelei": {"id": "0b66a153-548f-4f2c-b734-09a13b0bd163", "label": "Lorelei (Female, DE)", "lang": "de"},
    "nico": {"id": "afa425cf-5489-4a09-8a3f-d3cb1f82150d", "label": "Nico (Male, DE)", "lang": "de"},
    "lukas": {"id": "e00dd3df-19e7-4cd4-827a-7ff6687b6954", "label": "Lukas (Male, DE)", "lang": "de"},
    "andreas": {"id": "db229dfe-f5de-4be4-91fd-7b077c158578", "label": "Andreas (Male, DE)", "lang": "de"},
    "thomas": {"id": "384b625b-da5d-49e8-a76d-a2855d4f31eb", "label": "Thomas (Male, DE)", "lang": "de"},
    "sebastian": {"id": "b7187e84-fe22-4344-ba4a-bc013fcb533e", "label": "Sebastian (Male, DE)", "lang": "de"},
    # Legacy aliases
    "german-female": {"id": "b9de4a89-2257-424b-94c2-db18ba68c81a", "label": "Viktoria (Female, DE)", "lang": "de"},
    "german-male": {"id": "afa425cf-5489-4a09-8a3f-d3cb1f82150d", "label": "Nico (Male, DE)", "lang": "de"},

    # ── French ───────────────────────────────────────────────────────────
    "isabelle": {"id": "22f1a356-56c2-4428-bc91-2ab2e6d0c215", "label": "Isabelle (Female, FR)", "lang": "fr"},
    "marie-eve": {"id": "6d912a43-805f-4673-bbc8-a9e6c45a6ad0", "label": "Marie-Eve (Female, FR)", "lang": "fr"},
    "mika": {"id": "187d1cc5-a771-4ccd-9110-9df8c4e39499", "label": "Mika (Female, FR)", "lang": "fr"},
    "manon": {"id": "2f8e82c4-cb94-4e6d-8b6a-29bf58ceb60a", "label": "Manon (Female, FR)", "lang": "fr"},
    "eloise": {"id": "6c64b57a-bc65-48e4-bff4-12dbe85606cd", "label": "Eloise (Female, FR)", "lang": "fr"},
    "joris": {"id": "68db3d29-e0ab-4d4f-a5d5-e34ee47d38b7", "label": "Joris (Male, FR)", "lang": "fr"},
    "marc": {"id": "ce74c4da-4aee-435d-bc6d-81d1a9367e12", "label": "Marc (Male, FR)", "lang": "fr"},
    "gerard": {"id": "5deeaea9-c3cf-4288-82ec-22d8f04eb158", "label": "Gerard (Male, FR)", "lang": "fr"},
    "antoine": {"id": "0418348a-0ca2-4e90-9986-800fb8b3bbc0", "label": "Antoine (Male, FR)", "lang": "fr"},
    # Legacy aliases
    "french-female": {"id": "a8a1eb38-5f15-4c1d-8722-7ac0f329727d", "label": "Calm French Woman (FR)", "lang": "fr"},
    "french-male": {"id": "ab7c61f5-3daa-47dd-a23b-4ac0aac5f5c3", "label": "Friendly French Man (FR)", "lang": "fr"},

    # ── Spanish ──────────────────────────────────────────────────────────
    "isabel-es": {"id": "c0c374aa-09be-42d9-9828-4d2d7df86962", "label": "Isabel (Female, ES)", "lang": "es"},
    "carmen": {"id": "727f663b-0e90-4031-90f2-558b7334425b", "label": "Carmen (Female, ES)", "lang": "es"},
    "paloma": {"id": "d4db5fb9-f44b-4bd1-85fa-192e0f0d75f9", "label": "Paloma (Female, ES)", "lang": "es"},
    "elena": {"id": "cefcb124-080b-4655-b31f-932f3ee743de", "label": "Elena (Female, ES)", "lang": "es"},
    "camila-es": {"id": "30212483-5c20-479c-8121-f93cd24e30a6", "label": "Camila (Female, ES)", "lang": "es"},
    "luis": {"id": "b5aa8098-49ef-475d-89b0-c9262ecf33fd", "label": "Luis (Male, ES)", "lang": "es"},
    "pablo": {"id": "846fa30b-6e1a-49b9-b7df-6be47092a09a", "label": "Pablo (Male, ES)", "lang": "es"},
    "hector": {"id": "b042270c-d46f-4d4f-8fb0-7dd7c5fe5615", "label": "Hector (Male, ES)", "lang": "es"},
    "alejandro": {"id": "3a35daa1-ba81-451c-9b21-59332e9db2f3", "label": "Alejandro (Male, ES)", "lang": "es"},
    # Legacy aliases
    "spanish-female": {"id": "c0c374aa-09be-42d9-9828-4d2d7df86962", "label": "Isabel (Female, ES)", "lang": "es"},
    "spanish-male": {"id": "b5aa8098-49ef-475d-89b0-c9262ecf33fd", "label": "Luis (Male, ES)", "lang": "es"},

    # ── Italian ──────────────────────────────────────────────────────────
    "alessandra": {"id": "0e21713a-5e9a-428a-bed4-90d410b87f13", "label": "Alessandra (Female, IT)", "lang": "it"},
    "francesca": {"id": "d609f27f-f1a4-410f-85bb-10037b4fba99", "label": "Francesca (Female, IT)", "lang": "it"},
    "giulia": {"id": "36d94908-c5b9-4014-b521-e69aee5bead0", "label": "Giulia (Female, IT)", "lang": "it"},
    "liv-it": {"id": "d718e944-b313-4998-b011-d1cc078d4ef3", "label": "Liv (Female, IT)", "lang": "it"},
    "matteo": {"id": "408daed0-c597-4c27-aae8-fa0497d644bf", "label": "Matteo (Male, IT)", "lang": "it"},
    "giancarlo": {"id": "029c3c7a-b6d9-44f0-814b-200d849830ff", "label": "Giancarlo (Male, IT)", "lang": "it"},
    "luca": {"id": "e019ed7e-6079-4467-bc7f-b599a5dccf6f", "label": "Luca (Male, IT)", "lang": "it"},
    "marco": {"id": "79693aee-1207-4771-a01e-20c393c89e6f", "label": "Marco (Male, IT)", "lang": "it"},
    # Legacy aliases
    "italian-female": {"id": "0e21713a-5e9a-428a-bed4-90d410b87f13", "label": "Alessandra (Female, IT)", "lang": "it"},
    "italian-male": {"id": "408daed0-c597-4c27-aae8-fa0497d644bf", "label": "Matteo (Male, IT)", "lang": "it"},

    # ── Arabic ───────────────────────────────────────────────────────────
    "amira": {"id": "6304c635-6681-4f9e-85b6-a97f4d26461a", "label": "Amira (Female, AR)", "lang": "ar"},
    "maryam": {"id": "9825cf5f-6aff-412a-80c5-bc58a8d55bc4", "label": "Maryam (Female, AR)", "lang": "ar"},
    "nour": {"id": "fc923f89-1de5-4ddf-b93c-6da2ba63428a", "label": "Nour (Female, AR)", "lang": "ar"},
    "huda": {"id": "002622d8-19d0-4567-a16a-f99c7397c062", "label": "Huda (Female, AR)", "lang": "ar"},
    "omar": {"id": "e3087ad8-7018-4154-9a87-11577f916cd4", "label": "Omar (Male, AR)", "lang": "ar"},
    "hassan": {"id": "664aec8a-64a4-4437-8a0b-a61aa4f51fe6", "label": "Hassan (Male, AR)", "lang": "ar"},
    "khalid": {"id": "b0aa4612-81d2-4df3-9730-3fc064754b1f", "label": "Khalid (Male, AR)", "lang": "ar"},
    "walid": {"id": "f1cdfb4a-bf7d-4e83-916e-8f0802278315", "label": "Walid (Male, AR)", "lang": "ar"},

    # ── Russian ──────────────────────────────────────────────────────────
    "tatiana": {"id": "064b17af-d36b-4bfb-b003-be07dba1b649", "label": "Tatiana (Female, RU)", "lang": "ru"},
    "irina": {"id": "642014de-c0e3-4133-adc0-36b5309c23e6", "label": "Irina (Female, RU)", "lang": "ru"},
    "natalya": {"id": "779673f3-895f-4935-b6b5-b031dc78b319", "label": "Natalya (Female, RU)", "lang": "ru"},
    "olga": {"id": "9ed9f7e7-3ef6-4773-9dd3-ffcb479ca1f0", "label": "Olga (Female, RU)", "lang": "ru"},
    "dmitri": {"id": "888b7df4-e165-4852-bfec-0ab2b96aaa46", "label": "Dmitri (Male, RU)", "lang": "ru"},

    # ── Japanese ─────────────────────────────────────────────────────────
    "kaori": {"id": "44863732-e415-4084-8ba1-deabe34ce3d2", "label": "Kaori (Female, JA)", "lang": "ja"},
    "emi-ja": {"id": "c7eafe22-8b71-40cd-850b-c5a3bbd8f8d2", "label": "Emi (Female, JA)", "lang": "ja"},
    "yumiko": {"id": "2b568345-1d48-4047-b25f-7baccf842eb0", "label": "Yumiko (Female, JA)", "lang": "ja"},
    "aiko": {"id": "498e7f37-7fa3-4e2c-b8e2-8b6e9276f956", "label": "Aiko (Female, JA)", "lang": "ja"},
    "daisuke": {"id": "e8a863c6-22c7-4671-86ca-91cacffc038d", "label": "Daisuke (Male, JA)", "lang": "ja"},
    "kenji": {"id": "6b92f628-be90-497c-8f4c-3b035002df71", "label": "Kenji (Male, JA)", "lang": "ja"},
    "takashi": {"id": "b8e1169c-f16a-4064-a6e0-95054169e553", "label": "Takashi (Male, JA)", "lang": "ja"},

    # ── Korean ───────────────────────────────────────────────────────────
    "yuna": {"id": "cac92886-4b7c-4bc1-a524-e0f79c0381be", "label": "Yuna (Female, KO)", "lang": "ko"},
    "soojin": {"id": "cd6c48a9-774b-4397-98b4-9948c0a790f0", "label": "Soojin (Female, KO)", "lang": "ko"},
    "jiwoo": {"id": "15628352-2ede-4f1b-89e6-ceda0c983fbc", "label": "Jiwoo (Female, KO)", "lang": "ko"},
    "minho": {"id": "537a82ae-4926-4bfb-9aec-aff0b80a12a5", "label": "Minho (Male, KO)", "lang": "ko"},
    "ryeowook": {"id": "f7755efb-1848-4321-aa22-5e5be5d32486", "label": "Ryeowook (Male, KO)", "lang": "ko"},

    # ── Chinese ──────────────────────────────────────────────────────────
    "yue": {"id": "e90c6678-f0d3-4767-9883-5d0ecf5894a8", "label": "Yue (Female, ZH)", "lang": "zh"},
    "mei": {"id": "a53c3509-ec3f-425c-a223-977f5f7424dd", "label": "Mei (Female, ZH)", "lang": "zh"},
    "hua": {"id": "7a5d4663-88ae-47b7-808e-8f9b9ee4127b", "label": "Hua (Female, ZH)", "lang": "zh"},
    "lan": {"id": "bf32f849-7bc9-4b91-8c62-954588efcc30", "label": "Lan (Female, ZH)", "lang": "zh"},
    "kai-zh": {"id": "eda5bbff-1ff1-4886-8ef1-4e69a77640a0", "label": "Kai (Male, ZH)", "lang": "zh"},
    "tao": {"id": "c59c247b-6aa9-4ab6-91f9-9eabea7dc69e", "label": "Tao (Male, ZH)", "lang": "zh"},
    "hao": {"id": "16212f18-4955-4be9-a6cd-2196ce2c11d1", "label": "Hao (Male, ZH)", "lang": "zh"},

    # ── Portuguese ───────────────────────────────────────────────────────
    "beatriz": {"id": "d4b44b9a-82bc-4b65-b456-763fce4c52f9", "label": "Beatriz (Female, PT)", "lang": "pt"},
    "ana-paula": {"id": "1cf751f6-8749-43ab-98bd-230dd633abdb", "label": "Ana Paula (Female, PT)", "lang": "pt"},
    "luana": {"id": "700d1ee3-a641-4018-ba6e-899dcadc9e2b", "label": "Luana (Female, PT)", "lang": "pt"},
    "camilo": {"id": "5063f45b-d9e0-4095-b056-8f3ee055d411", "label": "Camilo (Male, PT)", "lang": "pt"},
    "felipe": {"id": "a37639f0-2f0a-4de4-9942-875a187af878", "label": "Felipe (Male, PT)", "lang": "pt"},
    "tiago": {"id": "6a360542-a117-4ed5-9e09-e8bf9b05eabb", "label": "Tiago (Male, PT)", "lang": "pt"},

    # ── Dutch ────────────────────────────────────────────────────────────
    "sanne": {"id": "0eb213fe-4658-45bc-9442-33a48b24b133", "label": "Sanne (Female, NL)", "lang": "nl"},
    "anneke": {"id": "ac317dac-1b8f-434f-b198-a490e2a4914d", "label": "Anneke (Female, NL)", "lang": "nl"},
    "bram": {"id": "4aa74047-d005-4463-ba2e-a0d9b261fb87", "label": "Bram (Male, NL)", "lang": "nl"},
    "daan": {"id": "9e8db62d-056f-47f3-b3b6-1b05767f9176", "label": "Daan (Male, NL)", "lang": "nl"},

    # ── Polish ───────────────────────────────────────────────────────────
    "kasia": {"id": "ea7b5eee-39d9-40b0-b241-1910cbca9c62", "label": "Kasia (Female, PL)", "lang": "pl"},
    "katarzyna": {"id": "575a5d29-1fdc-4d4e-9afa-5a9a71759864", "label": "Katarzyna (Female, PL)", "lang": "pl"},
    "tomek": {"id": "82a7fc13-2927-4e42-9b8a-bb1f9e506521", "label": "Tomek (Male, PL)", "lang": "pl"},
    "jakub": {"id": "2a3503b2-b6b6-4534-a224-e8c0679cec4a", "label": "Jakub (Male, PL)", "lang": "pl"},

    # ── Hindi ────────────────────────────────────────────────────────────
    "aarti": {"id": "9cebb910-d4b7-4a4a-85a4-12c79137724c", "label": "Aarti (Female, HI)", "lang": "hi"},
    "neha": {"id": "47f3bbb1-e98f-4e0c-92c5-5f0325e1e206", "label": "Neha (Female, HI)", "lang": "hi"},
    "kavita": {"id": "56e35e2d-6eb6-4226-ab8b-9776515a7094", "label": "Kavita (Female, HI)", "lang": "hi"},
    "ishan": {"id": "fd2ada67-c2d9-4afe-b474-6386b87d8fc3", "label": "Ishan (Male, HI)", "lang": "hi"},
    "rahul": {"id": "393dd459-f8d8-4c3e-a86b-ec43a1113d0b", "label": "Rahul (Male, HI)", "lang": "hi"},

    # ── Swedish ──────────────────────────────────────────────────────────
    "freja": {"id": "6c6b05bf-ae5f-4013-82ab-7348e99ffdb2", "label": "Freja (Female, SV)", "lang": "sv"},
    "ingrid": {"id": "f852eb8d-a177-48cd-bf63-7e4dcab61a36", "label": "Ingrid (Female, SV)", "lang": "sv"},
    "anders": {"id": "38a146c3-69d7-40ad-aada-76d5a2621758", "label": "Anders (Male, SV)", "lang": "sv"},
    "erik": {"id": "32a806e8-894e-41ad-a4d5-6d9154d7b1e6", "label": "Erik (Male, SV)", "lang": "sv"},
}

# Default Cartesia voices per language
CARTESIA_DEFAULT_VOICES = {
    "tr": "azra",
    "en": "katie",
    "de": "alina",
    "fr": "isabelle",
    "es": "isabel-es",
    "it": "alessandra",
    "ar": "amira",
    "ru": "tatiana",
    "ja": "kaori",
    "ko": "yuna",
    "zh": "yue",
    "pt": "beatriz",
    "nl": "sanne",
    "pl": "kasia",
    "hi": "aarti",
    "sv": "freja",
}


async def cartesia_synthesize(
    text: str,
    api_key: str,
    voice: str = "katie",
    language: str = "en",
    model: str = "sonic-3",
    sample_rate: int = 24000,
    speed: float = 1.0,
) -> bytes:
    """
    Synthesize speech using Cartesia Sonic TTS.

    Returns raw PCM16 mono audio at the requested sample rate.
    """
    # Resolve voice ID
    voice_info = CARTESIA_VOICES.get(voice)
    if voice_info:
        voice_id = voice_info["id"]
    else:
        # Assume raw voice ID was passed
        voice_id = voice

    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.cartesia.ai/tts/bytes",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Cartesia-Version": "2025-04-16",
                    "Content-Type": "application/json",
                },
                json={
                    "model_id": model,
                    "transcript": text,
                    "voice": {
                        "mode": "id",
                        "id": voice_id,
                    },
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": sample_rate,
                    },
                    "language": language,
                    "generation_config": {
                        "speed": speed,
                    },
                },
            )

            elapsed = (time.monotonic() - t0) * 1000

            if response.status_code != 200:
                logger.error(f"Cartesia TTS error {response.status_code}: {response.text[:200]}")
                return b""

            audio_data = response.content
            audio_duration_ms = len(audio_data) / (sample_rate * 2) * 1000
            rtf = elapsed / audio_duration_ms if audio_duration_ms > 0 else 0

            logger.info(
                f"Cartesia TTS: {len(audio_data)} bytes ({audio_duration_ms:.0f}ms audio) "
                f"in {elapsed:.0f}ms (RTF={rtf:.2f}) for '{text[:50]}'"
            )
            return audio_data

    except Exception as e:
        logger.error(f"Cartesia TTS error: {e}")
        return b""


# ============================================================================
# OPENAI TTS
# ============================================================================

OPENAI_TTS_VOICES = {
    "alloy": {"label": "Alloy (Neutral)", "lang": "multi"},
    "ash": {"label": "Ash (Male)", "lang": "multi"},
    "coral": {"label": "Coral (Female)", "lang": "multi"},
    "echo": {"label": "Echo (Male)", "lang": "multi"},
    "fable": {"label": "Fable (Male, British)", "lang": "multi"},
    "nova": {"label": "Nova (Female)", "lang": "multi"},
    "onyx": {"label": "Onyx (Male, Deep)", "lang": "multi"},
    "sage": {"label": "Sage (Female)", "lang": "multi"},
    "shimmer": {"label": "Shimmer (Female)", "lang": "multi"},
}


async def openai_synthesize(
    text: str,
    api_key: str,
    voice: str = "nova",
    model: str = "tts-1",
    speed: float = 1.0,
) -> bytes:
    """
    Synthesize speech using OpenAI TTS API.

    Returns raw PCM16 mono audio at 24kHz.
    Note: OpenAI TTS with response_format=pcm always returns 24kHz/16-bit/mono.
    """
    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": text,
                    "voice": voice,
                    "response_format": "pcm",
                    "speed": speed,
                },
            )

            elapsed = (time.monotonic() - t0) * 1000

            if response.status_code != 200:
                logger.error(f"OpenAI TTS error {response.status_code}: {response.text[:200]}")
                return b""

            audio_data = response.content
            # OpenAI PCM is always 24kHz
            audio_duration_ms = len(audio_data) / (24000 * 2) * 1000
            rtf = elapsed / audio_duration_ms if audio_duration_ms > 0 else 0

            logger.info(
                f"OpenAI TTS: {len(audio_data)} bytes ({audio_duration_ms:.0f}ms audio) "
                f"in {elapsed:.0f}ms (RTF={rtf:.2f}) for '{text[:50]}'"
            )
            return audio_data

    except Exception as e:
        logger.error(f"OpenAI TTS error: {e}")
        return b""


# ============================================================================
# DEEPGRAM TTS
# ============================================================================

DEEPGRAM_TTS_VOICES = {
    # English
    "aura-2-thalia-en": {"label": "Thalia (Female, EN)", "lang": "en"},
    "aura-2-andromeda-en": {"label": "Andromeda (Female, EN)", "lang": "en"},
    "aura-2-apollo-en": {"label": "Apollo (Male, EN)", "lang": "en"},
    "aura-2-arcas-en": {"label": "Arcas (Male, EN)", "lang": "en"},
    "aura-2-helena-en": {"label": "Helena (Female, EN)", "lang": "en"},
    "aura-2-zeus-en": {"label": "Zeus (Male, EN)", "lang": "en"},
    # German
    "aura-2-thalia-de": {"label": "Thalia (Female, DE)", "lang": "de"},
    "aura-2-apollo-de": {"label": "Apollo (Male, DE)", "lang": "de"},
    # French
    "aura-2-thalia-fr": {"label": "Thalia (Female, FR)", "lang": "fr"},
    "aura-2-apollo-fr": {"label": "Apollo (Male, FR)", "lang": "fr"},
    # Spanish
    "aura-2-thalia-es": {"label": "Thalia (Female, ES)", "lang": "es"},
    "aura-2-apollo-es": {"label": "Apollo (Male, ES)", "lang": "es"},
    # Italian
    "aura-2-thalia-it": {"label": "Thalia (Female, IT)", "lang": "it"},
    "aura-2-apollo-it": {"label": "Apollo (Male, IT)", "lang": "it"},
}

# Default Deepgram voices per language
DEEPGRAM_DEFAULT_VOICES = {
    "en": "aura-2-thalia-en",
    "de": "aura-2-thalia-de",
    "fr": "aura-2-thalia-fr",
    "es": "aura-2-thalia-es",
    "it": "aura-2-thalia-it",
    "tr": "aura-2-thalia-en",  # Turkish not natively supported, use English
}


async def deepgram_synthesize(
    text: str,
    api_key: str,
    voice: str = "aura-2-thalia-en",
    sample_rate: int = 24000,
) -> bytes:
    """
    Synthesize speech using Deepgram Aura TTS.

    Returns raw PCM16 mono audio at the requested sample rate.
    """
    url = (
        f"https://api.deepgram.com/v1/speak"
        f"?model={voice}"
        f"&encoding=linear16"
        f"&sample_rate={sample_rate}"
        f"&container=none"
    )

    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
            )

            elapsed = (time.monotonic() - t0) * 1000

            if response.status_code != 200:
                logger.error(f"Deepgram TTS error {response.status_code}: {response.text[:200]}")
                return b""

            audio_data = response.content
            audio_duration_ms = len(audio_data) / (sample_rate * 2) * 1000
            rtf = elapsed / audio_duration_ms if audio_duration_ms > 0 else 0

            logger.info(
                f"Deepgram TTS: {len(audio_data)} bytes ({audio_duration_ms:.0f}ms audio) "
                f"in {elapsed:.0f}ms (RTF={rtf:.2f}) for '{text[:50]}'"
            )
            return audio_data

    except Exception as e:
        logger.error(f"Deepgram TTS error: {e}")
        return b""


# ============================================================================
# TTS PROVIDER FACTORY
# ============================================================================

TTS_PROVIDERS = {
    "cartesia": {
        "label": "Cartesia Sonic",
        "models": ["sonic-3"],
        "default_model": "sonic-3",
        "env_key": "CARTESIA_API_KEY",
        "voices": CARTESIA_VOICES,
        "default_voices": CARTESIA_DEFAULT_VOICES,
        "output_sample_rate": 24000,  # Configurable per request
    },
    "openai": {
        "label": "OpenAI TTS",
        "models": ["tts-1", "tts-1-hd", "gpt-4o-mini-tts"],
        "default_model": "tts-1",
        "env_key": "OPENAI_API_KEY",
        "voices": OPENAI_TTS_VOICES,
        "default_voices": {lang: "nova" for lang in ["tr", "en", "de", "fr", "es", "it"]},
        "output_sample_rate": 24000,  # Always 24kHz for PCM
    },
    "deepgram": {
        "label": "Deepgram Aura",
        "models": [],
        "default_model": None,
        "env_key": "DEEPGRAM_API_KEY",
        "voices": DEEPGRAM_TTS_VOICES,
        "default_voices": DEEPGRAM_DEFAULT_VOICES,
        "output_sample_rate": 24000,  # Configurable per request
    },
}


async def cloud_synthesize(
    text: str,
    provider: str,
    api_key: str,
    voice: Optional[str] = None,
    language: str = "tr",
    model: Optional[str] = None,
    sample_rate: int = 24000,
    speed: float = 1.0,
) -> tuple[bytes, int]:
    """
    Unified TTS interface — dispatches to the correct provider.

    Args:
        text: Text to synthesize
        provider: "cartesia", "openai", or "deepgram"
        api_key: API key for the provider
        voice: Voice name/ID (uses language default if None)
        language: Language code
        model: Model override
        sample_rate: Desired output sample rate
        speed: Speech speed multiplier

    Returns:
        Tuple of (audio_bytes, actual_sample_rate)
        actual_sample_rate may differ from requested (e.g. OpenAI always 24kHz)
    """
    provider_config = TTS_PROVIDERS.get(provider)
    if not provider_config:
        logger.error(f"Unknown TTS provider: {provider}")
        return b"", sample_rate

    # Resolve voice
    if not voice:
        default_voices = provider_config.get("default_voices", {})
        voice = default_voices.get(language, list(default_voices.values())[0] if default_voices else "")

    if provider == "cartesia":
        audio = await cartesia_synthesize(
            text, api_key, voice=voice, language=language,
            model=model or "sonic-3", sample_rate=sample_rate, speed=speed,
        )
        return audio, sample_rate

    elif provider == "openai":
        audio = await openai_synthesize(
            text, api_key, voice=voice,
            model=model or "tts-1", speed=speed,
        )
        return audio, 24000  # OpenAI PCM is always 24kHz

    elif provider == "deepgram":
        audio = await deepgram_synthesize(
            text, api_key, voice=voice, sample_rate=sample_rate,
        )
        return audio, sample_rate

    else:
        logger.error(f"Unknown TTS provider: {provider}")
        return b"", sample_rate
