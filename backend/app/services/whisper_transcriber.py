"""
Post-call Whisper transcription service.

Provides a reliable fallback/complement to realtime transcription by
processing recorded audio through OpenAI Whisper API after the call ends.

Strategy:
  1. Realtime transcript (from provider events) → fast, used for live monitoring
  2. Whisper post-call transcript → accurate, used for DB persistence
  3. Merge: keep realtime for speed, replace/supplement with Whisper for accuracy

Audio is stored in Redis during the call as raw PCM16 24kHz data:
  - call_audio_input:{uuid}  → customer audio
  - call_audio_output:{uuid} → agent audio

This service reads those buffers, converts to WAV, sends to Whisper,
and returns structured transcript entries.
"""

import io
import struct
import time
from datetime import datetime
from typing import Optional

import aiohttp
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Whisper API endpoint
WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"

# Audio format constants (must match asterisk_bridge.py)
SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit PCM

# Whisper model — best accuracy
WHISPER_MODEL = "whisper-1"

# Maximum audio duration Whisper can process (25 minutes)
WHISPER_MAX_DURATION_SECONDS = 1500

# Minimum audio size to attempt transcription (0.5 second of audio)
MIN_AUDIO_BYTES = SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS  # ~48KB = 1 second


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    """
    Convert raw PCM16 mono audio to WAV format.

    Whisper API requires a proper audio file format (WAV, MP3, etc.),
    not raw PCM bytes.
    """
    buf = io.BytesIO()

    # WAV header
    data_size = len(pcm_data)
    file_size = 36 + data_size

    buf.write(b"RIFF")
    buf.write(struct.pack("<I", file_size))
    buf.write(b"WAVE")

    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size
    buf.write(struct.pack("<H", 1))   # PCM format
    buf.write(struct.pack("<H", CHANNELS))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * CHANNELS * SAMPLE_WIDTH))  # byte rate
    buf.write(struct.pack("<H", CHANNELS * SAMPLE_WIDTH))  # block align
    buf.write(struct.pack("<H", SAMPLE_WIDTH * 8))  # bits per sample

    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm_data)

    return buf.getvalue()


async def _transcribe_audio(
    wav_data: bytes,
    language: str = "tr",
    prompt: str = "",
) -> Optional[str]:
    """
    Send WAV audio to OpenAI Whisper API and return transcription text.

    Args:
        wav_data: WAV-formatted audio bytes
        language: ISO 639-1 language code
        prompt: Optional prompt to guide Whisper (e.g. domain-specific terms)

    Returns:
        Transcribed text or None on failure
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.warning("whisper_transcribe: OPENAI_API_KEY not configured")
        return None

    headers = {"Authorization": f"Bearer {api_key}"}

    form = aiohttp.FormData()
    form.add_field("file", wav_data, filename="audio.wav", content_type="audio/wav")
    form.add_field("model", WHISPER_MODEL)
    form.add_field("language", language)
    form.add_field("response_format", "verbose_json")
    form.add_field("timestamp_granularities[]", "segment")
    if prompt:
        form.add_field("prompt", prompt[:224])  # Whisper prompt max ~224 tokens

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WHISPER_API_URL,
                headers=headers,
                data=form,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(
                        "whisper_transcribe_failed",
                        status=resp.status,
                        error=error_text[:500],
                    )
                    return None

                result = await resp.json()
                return result

    except Exception as e:
        logger.error("whisper_transcribe_exception", error=str(e))
        return None


async def transcribe_call_audio(
    call_uuid: str,
    language: str = "tr",
    redis_url: str = "",
) -> dict:
    """
    Transcribe a completed call using audio buffers stored in Redis.

    Reads input (customer) and output (agent) audio separately,
    transcribes each through Whisper, and returns merged transcript.

    Args:
        call_uuid: The call UUID
        language: Language code for Whisper
        redis_url: Redis connection URL

    Returns:
        {
            "success": bool,
            "transcript_text": str,  # Formatted "[user]: ... \n [assistant]: ..."
            "messages": list,        # [{role, content, start, end}, ...]
            "input_duration": float,
            "output_duration": float,
            "method": "whisper",
        }
    """
    if not redis_url:
        redis_url = settings.REDIS_URL

    import redis.asyncio as redis_async

    result = {
        "success": False,
        "transcript_text": "",
        "messages": [],
        "input_duration": 0.0,
        "output_duration": 0.0,
        "method": "whisper",
    }

    t0 = time.monotonic()

    try:
        r = redis_async.from_url(redis_url, decode_responses=False)
        try:
            input_audio = await r.get(f"call_audio_input:{call_uuid}")
            output_audio = await r.get(f"call_audio_output:{call_uuid}")
        finally:
            await r.close()
    except Exception as e:
        logger.error("whisper_redis_read_failed", call=call_uuid[:8], error=str(e))
        return result

    input_size = len(input_audio) if input_audio else 0
    output_size = len(output_audio) if output_audio else 0

    logger.info(
        "whisper_audio_read",
        call=call_uuid[:8],
        input_bytes=input_size,
        output_bytes=output_size,
    )

    if input_size < MIN_AUDIO_BYTES and output_size < MIN_AUDIO_BYTES:
        logger.warning("whisper_audio_too_short", call=call_uuid[:8])
        return result

    # Calculate durations
    result["input_duration"] = input_size / (SAMPLE_RATE * SAMPLE_WIDTH) if input_size else 0
    result["output_duration"] = output_size / (SAMPLE_RATE * SAMPLE_WIDTH) if output_size else 0

    # Transcribe customer audio (input)
    input_segments = []
    if input_audio and input_size >= MIN_AUDIO_BYTES:
        wav_input = _pcm_to_wav(input_audio)
        input_result = await _transcribe_audio(wav_input, language=language)
        if input_result and isinstance(input_result, dict):
            segments = input_result.get("segments", [])
            for seg in segments:
                text = seg.get("text", "").strip()
                if text:
                    input_segments.append({
                        "role": "user",
                        "content": text,
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                    })
            logger.info(
                "whisper_input_done",
                call=call_uuid[:8],
                segments=len(input_segments),
                text_len=len(input_result.get("text", "")),
            )

    # Transcribe agent audio (output)
    output_segments = []
    if output_audio and output_size >= MIN_AUDIO_BYTES:
        wav_output = _pcm_to_wav(output_audio)
        output_result = await _transcribe_audio(wav_output, language=language)
        if output_result and isinstance(output_result, dict):
            segments = output_result.get("segments", [])
            for seg in segments:
                text = seg.get("text", "").strip()
                if text:
                    output_segments.append({
                        "role": "assistant",
                        "content": text,
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                    })
            logger.info(
                "whisper_output_done",
                call=call_uuid[:8],
                segments=len(output_segments),
                text_len=len(output_result.get("text", "")),
            )

    # Merge segments by timestamp for chronological order
    all_segments = input_segments + output_segments
    all_segments.sort(key=lambda s: s["start"])

    # Consolidate consecutive same-role segments
    merged: list[dict] = []
    for seg in all_segments:
        if merged and merged[-1]["role"] == seg["role"]:
            # Same speaker — append text
            merged[-1]["content"] += " " + seg["content"]
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(dict(seg))

    # Build formatted text
    lines = []
    for msg in merged:
        lines.append(f"[{msg['role']}]: {msg['content']}")

    elapsed = time.monotonic() - t0

    result["success"] = True
    result["messages"] = merged
    result["transcript_text"] = "\n".join(lines)

    logger.info(
        "whisper_transcribe_complete",
        call=call_uuid[:8],
        messages=len(merged),
        input_segs=len(input_segments),
        output_segs=len(output_segments),
        elapsed=f"{elapsed:.1f}s",
    )

    return result


def merge_transcripts(
    realtime_text: str,
    whisper_result: dict,
    min_realtime_messages: int = 3,
) -> str:
    """
    Merge realtime transcript with Whisper transcript.

    Strategy:
      - If realtime has enough content (>= min_realtime_messages), use Whisper
        only to fill gaps or validate
      - If realtime is empty/too short, use Whisper entirely
      - Whisper transcript is preferred for DB persistence (more accurate)

    Args:
        realtime_text: The "[role]: content" formatted realtime transcript
        whisper_result: Result from transcribe_call_audio()
        min_realtime_messages: Minimum message count to consider realtime "good enough"

    Returns:
        The best transcript text to persist in DB
    """
    whisper_text = whisper_result.get("transcript_text", "")
    whisper_messages = whisper_result.get("messages", [])

    if not whisper_text:
        # Whisper failed — keep realtime as-is
        return realtime_text

    # Count realtime messages
    realtime_lines = [l for l in realtime_text.split("\n") if l.strip()] if realtime_text else []
    realtime_count = len(realtime_lines)

    # If realtime is empty or very short, use Whisper entirely
    if realtime_count < min_realtime_messages:
        logger.info(
            "merge_using_whisper",
            realtime_count=realtime_count,
            whisper_count=len(whisper_messages),
            reason="realtime_insufficient",
        )
        return whisper_text

    # Both have content — use Whisper (more accurate timestamps and completeness)
    # But add a header noting both sources were available
    if len(whisper_messages) >= realtime_count:
        # Whisper has equal or more content — prefer it
        logger.info(
            "merge_using_whisper",
            realtime_count=realtime_count,
            whisper_count=len(whisper_messages),
            reason="whisper_more_complete",
        )
        return whisper_text

    # Realtime has more content than Whisper segments — keep realtime
    # (This can happen if Whisper merged too aggressively)
    logger.info(
        "merge_using_realtime",
        realtime_count=realtime_count,
        whisper_count=len(whisper_messages),
        reason="realtime_more_detailed",
    )
    return realtime_text
