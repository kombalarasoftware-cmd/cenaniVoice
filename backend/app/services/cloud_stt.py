"""
Cloud STT (Speech-to-Text) Providers
=====================================
Supported providers:
  - Deepgram (nova-3) — fastest, best accuracy
  - OpenAI (gpt-4o-transcribe, whisper-1)

All providers accept raw PCM16 audio and return transcribed text.
"""

import io
import wave
import time
import logging
from typing import Optional

import httpx

logger = logging.getLogger("pipeline-bridge")


# ============================================================================
# DEEPGRAM STT
# ============================================================================

async def deepgram_transcribe(
    pcm_data: bytes,
    api_key: str,
    language: str = "tr",
    sample_rate: int = 16000,
    model: str = "nova-3",
) -> str:
    """
    Transcribe audio using Deepgram REST API.

    Input: Raw PCM16 mono audio at specified sample_rate.
    Output: Transcribed text.
    """
    if len(pcm_data) < 3200:  # Less than 100ms
        return ""

    url = (
        f"https://api.deepgram.com/v1/listen"
        f"?model={model}"
        f"&language={language}"
        f"&encoding=linear16"
        f"&sample_rate={sample_rate}"
        f"&channels=1"
        f"&smart_format=true"
        f"&punctuate=true"
    )

    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "audio/raw",
                },
                content=pcm_data,
            )

            elapsed = (time.monotonic() - t0) * 1000

            if response.status_code != 200:
                logger.error(f"Deepgram STT error {response.status_code}: {response.text[:200]}")
                return ""

            data = response.json()
            transcript = (
                data.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("transcript", "")
            )

            audio_duration_ms = len(pcm_data) / (sample_rate * 2) * 1000
            logger.info(
                f"Deepgram STT ({elapsed:.0f}ms, audio={audio_duration_ms:.0f}ms): "
                f"'{transcript[:80]}'"
            )
            return transcript.strip()

    except Exception as e:
        logger.error(f"Deepgram STT error: {e}")
        return ""


# ============================================================================
# OPENAI STT
# ============================================================================

async def openai_transcribe(
    pcm_data: bytes,
    api_key: str,
    language: str = "tr",
    sample_rate: int = 16000,
    model: str = "gpt-4o-transcribe",
) -> str:
    """
    Transcribe audio using OpenAI REST API.

    Input: Raw PCM16 mono audio (converted to WAV for upload).
    Output: Transcribed text.

    Note: OpenAI requires file upload (WAV/MP3 etc.), not raw PCM.
    """
    if len(pcm_data) < 3200:
        return ""

    # Convert raw PCM16 to WAV in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    wav_bytes = wav_buffer.getvalue()

    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                files={
                    "file": ("audio.wav", wav_bytes, "audio/wav"),
                },
                data={
                    "model": model,
                    "language": language,
                    "response_format": "json",
                },
            )

            elapsed = (time.monotonic() - t0) * 1000

            if response.status_code != 200:
                logger.error(f"OpenAI STT error {response.status_code}: {response.text[:200]}")
                return ""

            data = response.json()
            transcript = data.get("text", "")

            audio_duration_ms = len(pcm_data) / (sample_rate * 2) * 1000
            logger.info(
                f"OpenAI STT ({elapsed:.0f}ms, audio={audio_duration_ms:.0f}ms): "
                f"'{transcript[:80]}'"
            )
            return transcript.strip()

    except Exception as e:
        logger.error(f"OpenAI STT error: {e}")
        return ""


# ============================================================================
# STT PROVIDER FACTORY
# ============================================================================

# Available STT providers with metadata
STT_PROVIDERS = {
    "deepgram": {
        "label": "Deepgram Nova-3",
        "models": ["nova-3", "nova-2", "nova"],
        "default_model": "nova-3",
        "env_key": "DEEPGRAM_API_KEY",
    },
    "openai": {
        "label": "OpenAI Whisper",
        "models": ["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"],
        "default_model": "gpt-4o-transcribe",
        "env_key": "OPENAI_API_KEY",
    },
}


async def cloud_transcribe(
    pcm_data: bytes,
    provider: str,
    api_key: str,
    language: str = "tr",
    sample_rate: int = 16000,
    model: Optional[str] = None,
) -> str:
    """
    Unified STT interface — dispatches to the correct provider.

    Args:
        pcm_data: Raw PCM16 mono audio
        provider: "deepgram" or "openai"
        api_key: API key for the provider
        language: Language code (e.g. "tr", "en", "de")
        sample_rate: Audio sample rate (default 16kHz)
        model: Model override (uses provider default if None)
    """
    if provider == "deepgram":
        return await deepgram_transcribe(
            pcm_data, api_key, language, sample_rate,
            model=model or STT_PROVIDERS["deepgram"]["default_model"],
        )
    elif provider == "openai":
        return await openai_transcribe(
            pcm_data, api_key, language, sample_rate,
            model=model or STT_PROVIDERS["openai"]["default_model"],
        )
    else:
        logger.error(f"Unknown STT provider: {provider}")
        return ""
