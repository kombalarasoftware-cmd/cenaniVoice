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

# Popular Cartesia voices (voice IDs)
CARTESIA_VOICES = {
    # English
    "katie": {"id": "f786b574-daa5-4673-aa0c-cbe3e8534c02", "label": "Katie (Female, EN)", "lang": "en"},
    "kiefer": {"id": "228fca29-3a0a-435c-8728-5cb483251068", "label": "Kiefer (Male, EN)", "lang": "en"},
    "tessa": {"id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b", "label": "Tessa (Female, EN)", "lang": "en"},
    "kyle": {"id": "c961b81c-a935-4c17-bfb3-ba2239de8c2f", "label": "Kyle (Male, EN)", "lang": "en"},
    "sarah": {"id": "694f9389-aac1-45b6-b726-9d9369183238", "label": "Sarah (Female, EN)", "lang": "en"},
    # Turkish (Cartesia supports Turkish with sonic-3)
    "turkish-female": {"id": "2e4e4f37-d912-4aa3-88d0-bfaa6f29f3b8", "label": "Turkish Female", "lang": "tr"},
    "turkish-male": {"id": "07c94b80-455a-4e34-9e30-f2937cbb3c87", "label": "Turkish Male", "lang": "tr"},
    # German
    "german-female": {"id": "b9de4a89-2257-424b-94c2-db18ba68c81a", "label": "German Female", "lang": "de"},
    "german-male": {"id": "fb26447f-308b-471e-8b00-4ef9572b9bae", "label": "German Male", "lang": "de"},
    # French
    "french-female": {"id": "a8a1eb38-5f15-4c1d-8722-7ac0f329a8f3", "label": "French Female", "lang": "fr"},
    "french-male": {"id": "5c3c89e5-535f-43ef-b08d-6d39d6277100", "label": "French Male", "lang": "fr"},
    # Spanish
    "spanish-female": {"id": "846d6cb0-2301-48b6-9683-48f5618ea2f6", "label": "Spanish Female", "lang": "es"},
    "spanish-male": {"id": "34bde396-9fde-4eb9-88a8-da3f1e33ca7c", "label": "Spanish Male", "lang": "es"},
    # Italian
    "italian-female": {"id": "d46abd1d-2571-45e1-a4c0-5e1d30fba217", "label": "Italian Female", "lang": "it"},
    "italian-male": {"id": "029c3559-3303-4e69-8a0b-e2e69bef42d5", "label": "Italian Male", "lang": "it"},
}

# Default Cartesia voices per language
CARTESIA_DEFAULT_VOICES = {
    "tr": "turkish-female",
    "en": "katie",
    "de": "german-female",
    "fr": "french-female",
    "es": "spanish-female",
    "it": "italian-female",
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
