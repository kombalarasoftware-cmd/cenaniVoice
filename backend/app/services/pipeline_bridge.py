"""
Pipeline AudioSocket Bridge - Local STT + LLM + TTS
=====================================================
Bridges Asterisk AudioSocket with local AI pipeline:
  - Faster-Whisper (STT) — CPU-optimized speech recognition
  - Ollama (LLM) — Local language model (Qwen 2.5 7B default)
  - Piper TTS — CPU-optimized text-to-speech

Architecture:
    Phone → SIP Trunk → Asterisk → AudioSocket (TCP:9093)
                                          ↕
                                  Pipeline Bridge (this file)
                                    ↕        ↕         ↕
                              Whisper    Ollama     Piper TTS
                               (STT)     (LLM)      (TTS)

Audio Flow:
    Asterisk (slin24 24kHz PCM16) → resample 16kHz → Whisper STT
    Whisper text → Ollama LLM → response text
    Response text → Piper TTS → resample 24kHz → Asterisk

Requirements:
    pip install faster-whisper httpx websockets numpy

Usage:
    python -m app.services.pipeline_bridge
"""

import asyncio
import json
import os
import sys
import struct
import uuid
import time
import logging
import signal
import socket
import io
import wave
import array
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("numpy required: pip install numpy")
    sys.exit(1)

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("pipeline-bridge")

# ============================================================================
# CONFIGURATION
# ============================================================================

AUDIOSOCKET_HOST = os.environ.get("PIPELINE_AUDIOSOCKET_HOST", "0.0.0.0")
AUDIOSOCKET_PORT = int(os.environ.get("PIPELINE_AUDIOSOCKET_PORT", "9093"))

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

PIPER_HOST = os.environ.get("PIPER_HOST", "piper")
PIPER_PORT = int(os.environ.get("PIPER_PORT", "10200"))

WHISPER_MODEL = os.environ.get("FASTER_WHISPER_MODEL", "base")
WHISPER_DEVICE = os.environ.get("FASTER_WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.environ.get("FASTER_WHISPER_COMPUTE", "int8")

MAX_CONCURRENT_CALLS = int(os.environ.get("MAX_CONCURRENT_CALLS", "10"))

# Redis
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# PostgreSQL
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres")
DB_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME = os.environ.get("POSTGRES_DB", "voiceai")
DB_USER = os.environ.get("POSTGRES_USER", "")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")

# Audio constants
ASTERISK_SAMPLE_RATE = 24000   # slin24 from AudioSocket
WHISPER_SAMPLE_RATE = 16000    # Whisper expects 16kHz
PIPER_SAMPLE_RATE = 22050      # Piper outputs 22050Hz (model dependent)
CHUNK_DURATION_MS = 20

# AudioSocket protocol constants
MSG_HANGUP = 0x00
MSG_UUID = 0x01
MSG_DTMF = 0x03
MSG_AUDIO_8K = 0x10
MSG_AUDIO_16K = 0x12
MSG_AUDIO_24K = 0x13
MSG_AUDIO_48K = 0x16
MSG_ERROR = 0xFF
AUDIO_MSG_TYPES = {MSG_AUDIO_8K, MSG_AUDIO_16K, MSG_AUDIO_24K, MSG_AUDIO_48K}

# Voice Activity Detection thresholds
VAD_ENERGY_THRESHOLD = 500      # Minimum RMS energy to consider speech
VAD_SILENCE_TIMEOUT_MS = 1200   # Silence duration to trigger end of utterance
VAD_MIN_SPEECH_MS = 200         # Minimum speech duration to process

# Piper voice mapping per language
PIPER_VOICES = {
    "tr": "tr_TR-dfki-medium",
    "de": "de_DE-thorsten-medium",
    "en": "en_US-amy-medium",
    "fr": "fr_FR-siwis-medium",
    "es": "es_ES-sharvard-medium",
    "it": "it_IT-riccardo-x_low",
}

# ============================================================================
# WHISPER STT - Lazy loaded singleton
# ============================================================================

_whisper_model = None


def get_whisper_model():
    """Lazy-load Faster-Whisper model (singleton)."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Faster-Whisper model: {WHISPER_MODEL} (device={WHISPER_DEVICE}, compute={WHISPER_COMPUTE})")
            _whisper_model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE,
            )
            logger.info("Faster-Whisper model loaded successfully")
        except ImportError:
            logger.error("faster-whisper not installed: pip install faster-whisper")
            raise
    return _whisper_model


# ============================================================================
# AUDIO RESAMPLING UTILITIES
# ============================================================================

def resample_pcm16(pcm_data: bytes, from_rate: int, to_rate: int) -> bytes:
    """Resample PCM16 audio using linear interpolation (no scipy needed)."""
    if from_rate == to_rate:
        return pcm_data

    samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
    duration = len(samples) / from_rate
    new_length = int(duration * to_rate)

    if new_length == 0:
        return b""

    # Linear interpolation resampling
    old_indices = np.linspace(0, len(samples) - 1, new_length)
    new_samples = np.interp(old_indices, np.arange(len(samples)), samples)

    return new_samples.astype(np.int16).tobytes()


def pcm16_to_wav_bytes(pcm_data: bytes, sample_rate: int) -> bytes:
    """Convert raw PCM16 mono to WAV format in memory."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def rms_energy(pcm_data: bytes) -> float:
    """Calculate RMS energy of PCM16 audio."""
    if len(pcm_data) < 2:
        return 0.0
    samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float64)
    return float(np.sqrt(np.mean(samples ** 2)))


# ============================================================================
# REDIS HELPERS
# ============================================================================

async def get_call_setup_from_redis(call_uuid: str) -> Optional[Dict[str, Any]]:
    """Get call setup data from Redis (stored by backend when call initiated)."""
    try:
        import redis.asyncio as redis_async
        r = redis_async.from_url(REDIS_URL, decode_responses=True)
        try:
            data = await r.get(f"call_setup:{call_uuid}")
            if data:
                result = json.loads(data)
                logger.info(f"[{call_uuid[:8]}] Redis agent config found: agent_id={result.get('agent_id')}")
                return result
            else:
                logger.info(f"[{call_uuid[:8]}] No call setup in Redis (may be inbound)")
        finally:
            await r.close()
    except Exception as e:
        logger.warning(f"[{call_uuid[:8]}] Redis lookup error: {e}")
    return None


async def save_transcript_to_redis(call_uuid: str, role: str, content: str) -> bool:
    """Save transcript message to Redis for real-time frontend access."""
    try:
        import redis.asyncio as redis_async
        r = redis_async.from_url(REDIS_URL, decode_responses=True)
        try:
            transcript_key = f"call_transcript:{call_uuid}"
            message = json.dumps({
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            })
            await r.lpush(transcript_key, message)
            await r.expire(transcript_key, 3600)
            return True
        finally:
            await r.close()
    except Exception as e:
        logger.warning(f"[{call_uuid[:8]}] Transcript save error: {e}")
    return False


async def get_agent_from_db(agent_id: int) -> Optional[Dict[str, Any]]:
    """Get agent details from PostgreSQL."""
    try:
        import asyncpg
        dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        conn = await asyncpg.connect(dsn)
        try:
            row = await conn.fetchrow(
                "SELECT * FROM agents WHERE id = $1", agent_id
            )
            if row:
                return dict(row)
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"DB lookup error for agent {agent_id}: {e}")
    return None


# ============================================================================
# PIPER TTS CLIENT (Wyoming Protocol)
# ============================================================================

async def synthesize_speech(text: str, voice: str = "tr_TR-dfki-medium") -> bytes:
    """
    Synthesize speech using Piper TTS via Wyoming protocol.

    Returns raw PCM16 audio at Piper's native sample rate (usually 22050Hz).
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(PIPER_HOST, PIPER_PORT),
            timeout=5.0,
        )

        # Wyoming protocol: send JSON event + text
        # synthesize event
        event = {
            "type": "synthesize",
            "data": {
                "text": text,
                "voice": {"name": voice},
            },
        }
        event_str = json.dumps(event)
        event_bytes = event_str.encode("utf-8")

        # Wyoming framing: event length (4 bytes big-endian) + event JSON
        writer.write(struct.pack(">I", len(event_bytes)))
        writer.write(event_bytes)
        await writer.drain()

        # Read audio response
        audio_chunks = []
        try:
            while True:
                # Read event header
                header = await asyncio.wait_for(reader.read(4), timeout=30.0)
                if len(header) < 4:
                    break
                event_len = struct.unpack(">I", header)[0]
                if event_len == 0:
                    break
                event_data = await asyncio.wait_for(reader.read(event_len), timeout=10.0)
                resp_event = json.loads(event_data.decode("utf-8"))

                if resp_event.get("type") == "audio-chunk":
                    # Read audio payload
                    payload_len = resp_event.get("data", {}).get("payload_length", 0)
                    if payload_len > 0:
                        audio = await asyncio.wait_for(reader.read(payload_len), timeout=10.0)
                        audio_chunks.append(audio)
                elif resp_event.get("type") == "audio-stop":
                    break
        except asyncio.TimeoutError:
            pass

        writer.close()
        await writer.wait_closed()

        if audio_chunks:
            return b"".join(audio_chunks)
        return b""

    except Exception as e:
        logger.error(f"Piper TTS error: {e}")
        # Fallback: try HTTP-based Piper if Wyoming fails
        return await _synthesize_speech_http(text, voice)


async def _synthesize_speech_http(text: str, voice: str) -> bytes:
    """Fallback: synthesize via Piper HTTP API (if available)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://{PIPER_HOST}:{PIPER_PORT}/api/tts",
                json={"text": text, "voice": voice},
            )
            if response.status_code == 200:
                return response.content
    except Exception as e:
        logger.error(f"Piper HTTP fallback error: {e}")
    return b""


# ============================================================================
# OLLAMA LLM CLIENT
# ============================================================================

async def generate_llm_response(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 300,
) -> str:
    """
    Generate text response from Ollama LLM.

    Uses streaming for faster time-to-first-token.
    Returns the full response text.
    """
    model = model or OLLAMA_MODEL

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "top_p": 0.9,
                    },
                },
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            else:
                logger.error(f"Ollama error {response.status_code}: {response.text[:200]}")
                return ""
    except Exception as e:
        logger.error(f"Ollama LLM error: {e}")
        return ""


async def generate_llm_response_streaming(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 300,
):
    """
    Stream text response from Ollama LLM.

    Yields text chunks as they arrive for sentence-level TTS pipelining.
    """
    model = model or OLLAMA_MODEL

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "top_p": 0.9,
                    },
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        logger.error(f"Ollama streaming error: {e}")


# ============================================================================
# WHISPER STT
# ============================================================================

async def transcribe_audio(pcm_data: bytes, language: str = "tr") -> str:
    """
    Transcribe audio using Faster-Whisper.

    Input: PCM16 mono at 16kHz
    Output: Transcribed text
    """
    if len(pcm_data) < 3200:  # Less than 100ms of audio
        return ""

    # Run in executor to avoid blocking event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, pcm_data, language)


def _transcribe_sync(pcm_data: bytes, language: str) -> str:
    """Synchronous Whisper transcription (runs in thread pool)."""
    try:
        model = get_whisper_model()

        # Convert PCM16 to float32 normalized
        samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0

        # Map language codes
        whisper_lang_map = {
            "tr": "tr",
            "de": "de",
            "en": "en",
            "fr": "fr",
            "es": "es",
            "it": "it",
        }
        lang = whisper_lang_map.get(language, "tr")

        segments, info = model.transcribe(
            samples,
            language=lang,
            beam_size=3,
            best_of=3,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
        )

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        return " ".join(text_parts).strip()

    except Exception as e:
        logger.error(f"Whisper transcription error: {e}")
        return ""


# ============================================================================
# CALL SESSION
# ============================================================================

@dataclass
class PipelineCallSession:
    """Active call session state."""
    call_uuid: str
    agent_config: Dict[str, Any] = field(default_factory=dict)
    language: str = "tr"
    voice: str = "tr_TR-dfki-medium"
    model: str = "qwen2.5:7b"
    temperature: float = 0.7
    system_prompt: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    # Audio buffers
    audio_buffer: bytes = b""
    is_speaking: bool = False
    speech_start_time: float = 0.0
    last_speech_time: float = 0.0

    # State
    connected_at: Optional[datetime] = None
    greeting_sent: bool = False
    ai_speaking: bool = False

    # Stats
    total_user_messages: int = 0
    total_ai_messages: int = 0


# ============================================================================
# PIPELINE CALL HANDLER
# ============================================================================

class PipelineCallHandler:
    """
    Handles a single call session through the local pipeline.

    Flow per turn:
    1. Collect audio from Asterisk (with VAD)
    2. When silence detected → transcribe with Whisper
    3. Send transcript to Ollama LLM
    4. Stream LLM response → synthesize with Piper TTS
    5. Send TTS audio back to Asterisk
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.session: Optional[PipelineCallSession] = None
        self._running = False
        self._tts_queue: asyncio.Queue = asyncio.Queue()
        self._interrupt_event = asyncio.Event()

    async def handle(self):
        """Main call handling loop."""
        peer = self.writer.get_extra_info("peername")
        logger.info(f"New connection from {peer}")

        try:
            # Step 1: Read UUID from AudioSocket
            call_uuid = await self._read_uuid()
            if not call_uuid:
                logger.error("No UUID received, closing connection")
                return

            logger.info(f"[{call_uuid[:8]}] Call started")

            # Step 2: Get agent config from Redis
            agent_config = await get_call_setup_from_redis(call_uuid) or {}
            language = agent_config.get("language", "tr")
            voice = PIPER_VOICES.get(language, PIPER_VOICES["tr"])

            # Pipeline-specific model from agent config or default
            pipeline_model = agent_config.get("pipeline_model", OLLAMA_MODEL)

            # Build system prompt
            system_prompt = agent_config.get("prompt", "")
            if not system_prompt:
                system_prompt = self._build_default_prompt(language)

            self.session = PipelineCallSession(
                call_uuid=call_uuid,
                agent_config=agent_config,
                language=language,
                voice=voice,
                model=pipeline_model,
                temperature=agent_config.get("temperature", 0.7),
                system_prompt=system_prompt,
                connected_at=datetime.utcnow(),
            )

            # Initialize conversation with system prompt
            self.session.conversation_history.append({
                "role": "system",
                "content": system_prompt,
            })

            self._running = True

            # Start TTS playback task
            tts_task = asyncio.create_task(self._tts_playback_loop())

            # Send greeting if agent speaks first
            first_speaker = agent_config.get("first_speaker", "agent")
            if first_speaker == "agent":
                greeting = agent_config.get("greeting_message", "")
                if greeting:
                    # Process greeting variables
                    customer_name = agent_config.get("customer_name", "")
                    if customer_name and "{customer_name}" in greeting:
                        greeting = greeting.replace("{customer_name}", customer_name)
                    await self._speak(greeting)
                    self.session.greeting_sent = True

            # Step 3: Main audio processing loop
            await self._audio_loop()

        except asyncio.CancelledError:
            logger.info(f"[{self.session.call_uuid[:8] if self.session else '?'}] Call cancelled")
        except Exception as e:
            logger.error(f"Call handler error: {e}", exc_info=True)
        finally:
            self._running = False
            if self.session:
                logger.info(
                    f"[{self.session.call_uuid[:8]}] Call ended. "
                    f"User msgs: {self.session.total_user_messages}, "
                    f"AI msgs: {self.session.total_ai_messages}"
                )
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass

    async def _read_uuid(self) -> Optional[str]:
        """Read UUID from AudioSocket handshake."""
        try:
            header = await asyncio.wait_for(self.reader.read(3), timeout=10.0)
            if len(header) < 3:
                return None

            msg_type = header[0]
            payload_len = struct.unpack(">H", header[1:3])[0]

            if msg_type != MSG_UUID:
                logger.warning(f"Expected UUID message (0x01), got 0x{msg_type:02x}")
                return None

            payload = await asyncio.wait_for(self.reader.read(payload_len), timeout=5.0)
            call_uuid = payload.decode("utf-8", errors="replace").strip("\x00")

            # Validate UUID format
            try:
                uuid.UUID(call_uuid)
            except ValueError:
                # Try extracting UUID from payload bytes
                if len(payload) == 16:
                    call_uuid = str(uuid.UUID(bytes=payload))
                else:
                    call_uuid = str(uuid.uuid4())
                    logger.warning(f"Invalid UUID, generated new: {call_uuid[:8]}")

            return call_uuid

        except Exception as e:
            logger.error(f"UUID read error: {e}")
            return None

    async def _audio_loop(self):
        """
        Main audio receive loop with Voice Activity Detection.

        Collects audio, detects speech boundaries, triggers transcription.
        """
        silence_start = time.monotonic()
        speech_buffer = bytearray()
        is_speaking = False
        speech_start = 0.0

        while self._running:
            try:
                # Read AudioSocket frame header (3 bytes: type + length)
                header = await asyncio.wait_for(self.reader.read(3), timeout=30.0)
                if len(header) < 3:
                    logger.info(f"[{self.session.call_uuid[:8]}] Connection closed")
                    break

                msg_type = header[0]
                payload_len = struct.unpack(">H", header[1:3])[0]

                if msg_type == MSG_HANGUP:
                    logger.info(f"[{self.session.call_uuid[:8]}] Hangup received")
                    break

                if msg_type == MSG_ERROR:
                    logger.warning(f"[{self.session.call_uuid[:8]}] AudioSocket error")
                    break

                if msg_type not in AUDIO_MSG_TYPES:
                    # Skip non-audio messages
                    if payload_len > 0:
                        await self.reader.read(payload_len)
                    continue

                # Read audio payload
                if payload_len == 0:
                    continue

                audio_data = await asyncio.wait_for(
                    self.reader.read(payload_len), timeout=5.0
                )

                # If AI is currently speaking, check for interruption
                if self.session.ai_speaking:
                    energy = rms_energy(audio_data)
                    if energy > VAD_ENERGY_THRESHOLD * 1.5:
                        # User is trying to speak while AI talks → interrupt
                        self._interrupt_event.set()
                        self.session.ai_speaking = False
                        # Clear TTS queue
                        while not self._tts_queue.empty():
                            try:
                                self._tts_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                    continue  # Don't collect audio while AI speaks

                # VAD: check energy level
                energy = rms_energy(audio_data)
                now = time.monotonic()

                if energy > VAD_ENERGY_THRESHOLD:
                    if not is_speaking:
                        is_speaking = True
                        speech_start = now
                        speech_buffer = bytearray()
                        logger.debug(f"[{self.session.call_uuid[:8]}] Speech start (energy={energy:.0f})")

                    speech_buffer.extend(audio_data)
                    silence_start = now

                elif is_speaking:
                    # Still collecting but silence detected
                    speech_buffer.extend(audio_data)
                    silence_duration_ms = (now - silence_start) * 1000

                    if silence_duration_ms >= VAD_SILENCE_TIMEOUT_MS:
                        # End of utterance
                        speech_duration_ms = (now - speech_start) * 1000

                        if speech_duration_ms >= VAD_MIN_SPEECH_MS:
                            logger.info(
                                f"[{self.session.call_uuid[:8]}] Speech end: "
                                f"{speech_duration_ms:.0f}ms, {len(speech_buffer)} bytes"
                            )
                            # Process utterance
                            await self._process_utterance(bytes(speech_buffer))

                        is_speaking = False
                        speech_buffer = bytearray()

            except asyncio.TimeoutError:
                # No audio for 30 seconds
                logger.info(f"[{self.session.call_uuid[:8]}] Audio timeout")
                break
            except ConnectionError:
                logger.info(f"[{self.session.call_uuid[:8]}] Connection lost")
                break

    async def _process_utterance(self, audio_data: bytes):
        """Process a complete utterance: STT → LLM → TTS."""
        try:
            # Step 1: Resample 24kHz → 16kHz for Whisper
            audio_16k = resample_pcm16(audio_data, ASTERISK_SAMPLE_RATE, WHISPER_SAMPLE_RATE)

            # Step 2: Transcribe with Whisper
            t0 = time.monotonic()
            text = await transcribe_audio(audio_16k, self.session.language)
            stt_time = (time.monotonic() - t0) * 1000

            if not text or len(text.strip()) < 2:
                logger.debug(f"[{self.session.call_uuid[:8]}] Empty transcription, skipping")
                return

            logger.info(f"[{self.session.call_uuid[:8]}] STT ({stt_time:.0f}ms): {text}")
            self.session.total_user_messages += 1

            # Save to Redis
            await save_transcript_to_redis(self.session.call_uuid, "user", text)

            # Step 3: Add to conversation and get LLM response
            self.session.conversation_history.append({
                "role": "user",
                "content": text,
            })

            t0 = time.monotonic()

            # Use streaming for sentence-level TTS pipelining
            full_response = ""
            sentence_buffer = ""

            async for chunk in generate_llm_response_streaming(
                messages=self.session.conversation_history,
                model=self.session.model,
                temperature=self.session.temperature,
                max_tokens=300,
            ):
                full_response += chunk
                sentence_buffer += chunk

                # Check for sentence boundaries for early TTS
                for sep in [".", "!", "?", "...", "\n"]:
                    if sep in sentence_buffer:
                        parts = sentence_buffer.split(sep, 1)
                        sentence = parts[0] + sep
                        sentence_buffer = parts[1] if len(parts) > 1 else ""

                        sentence = sentence.strip()
                        if len(sentence) > 3:
                            # Queue sentence for TTS immediately
                            await self._tts_queue.put(sentence)
                            break

            # Process remaining buffer
            if sentence_buffer.strip() and len(sentence_buffer.strip()) > 3:
                await self._tts_queue.put(sentence_buffer.strip())

            # Signal end of response
            await self._tts_queue.put(None)

            llm_time = (time.monotonic() - t0) * 1000
            logger.info(f"[{self.session.call_uuid[:8]}] LLM ({llm_time:.0f}ms): {full_response[:100]}...")

            # Save to history and Redis
            self.session.conversation_history.append({
                "role": "assistant",
                "content": full_response,
            })
            self.session.total_ai_messages += 1
            await save_transcript_to_redis(self.session.call_uuid, "assistant", full_response)

            # Keep conversation history manageable
            if len(self.session.conversation_history) > 20:
                # Keep system prompt + last 16 messages
                self.session.conversation_history = (
                    self.session.conversation_history[:1]
                    + self.session.conversation_history[-16:]
                )

        except Exception as e:
            logger.error(f"[{self.session.call_uuid[:8]}] Utterance processing error: {e}", exc_info=True)

    async def _speak(self, text: str):
        """Synthesize and queue text for playback."""
        if not text.strip():
            return

        # Split long text into sentences for faster first-audio
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in ".!?\n" and len(current.strip()) > 3:
                sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())

        for sentence in sentences:
            await self._tts_queue.put(sentence)
        await self._tts_queue.put(None)  # Signal end

    async def _tts_playback_loop(self):
        """Background task: synthesize and play TTS audio."""
        while self._running:
            try:
                sentence = await asyncio.wait_for(self._tts_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if sentence is None:
                self.session.ai_speaking = False
                continue

            try:
                self.session.ai_speaking = True
                self._interrupt_event.clear()

                # Synthesize with Piper
                t0 = time.monotonic()
                tts_audio = await synthesize_speech(sentence, self.session.voice)
                tts_time = (time.monotonic() - t0) * 1000

                if not tts_audio:
                    logger.warning(f"[{self.session.call_uuid[:8]}] TTS returned empty audio")
                    continue

                logger.debug(f"[{self.session.call_uuid[:8]}] TTS ({tts_time:.0f}ms): {sentence[:50]}...")

                # Resample Piper output (22050Hz) → Asterisk (24000Hz)
                audio_24k = resample_pcm16(tts_audio, PIPER_SAMPLE_RATE, ASTERISK_SAMPLE_RATE)

                # Send in chunks matching Asterisk expectations
                chunk_size = ASTERISK_SAMPLE_RATE * CHUNK_DURATION_MS // 1000 * 2  # 960 bytes for 20ms
                offset = 0

                while offset < len(audio_24k) and not self._interrupt_event.is_set():
                    chunk = audio_24k[offset:offset + chunk_size]

                    # Pad last chunk if needed
                    if len(chunk) < chunk_size:
                        chunk += b"\x00" * (chunk_size - len(chunk))

                    # AudioSocket frame: type (1b) + length (2b) + payload
                    frame = struct.pack(">BH", MSG_AUDIO_24K, len(chunk)) + chunk

                    try:
                        self.writer.write(frame)
                        await self.writer.drain()
                    except (ConnectionError, BrokenPipeError):
                        self._running = False
                        return

                    offset += chunk_size

                    # Pace output to match real-time
                    await asyncio.sleep(CHUNK_DURATION_MS / 1000.0 * 0.8)

                if self._interrupt_event.is_set():
                    logger.info(f"[{self.session.call_uuid[:8]}] TTS interrupted by user")
                    # Drain remaining queue
                    while not self._tts_queue.empty():
                        try:
                            self._tts_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

            except Exception as e:
                logger.error(f"[{self.session.call_uuid[:8]}] TTS playback error: {e}")

        self.session.ai_speaking = False

    def _build_default_prompt(self, language: str) -> str:
        """Build a default system prompt if none provided."""
        prompts = {
            "tr": (
                "Sen yardımsever bir telefon asistanısın. Kısa ve net cevaplar ver. "
                "Doğal bir şekilde konuş, liste veya madde işareti kullanma. "
                "Her seferinde tek soru sor ve cevabı bekle."
            ),
            "de": (
                "Sie sind ein hilfreicher Telefonassistent. Geben Sie kurze und klare Antworten. "
                "Sprechen Sie natürlich, verwenden Sie keine Listen oder Aufzählungen. "
                "Stellen Sie jeweils nur eine Frage und warten Sie auf die Antwort."
            ),
            "en": (
                "You are a helpful phone assistant. Give short and clear answers. "
                "Speak naturally, do not use lists or bullet points. "
                "Ask only one question at a time and wait for the answer."
            ),
        }
        return prompts.get(language, prompts["en"])


# ============================================================================
# AUDIOSOCKET SERVER
# ============================================================================

active_calls: Dict[str, PipelineCallHandler] = {}
call_semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle incoming AudioSocket connection."""
    if not call_semaphore._value:
        logger.warning("Max concurrent calls reached, rejecting connection")
        writer.close()
        await writer.wait_closed()
        return

    async with call_semaphore:
        handler = PipelineCallHandler(reader, writer)
        await handler.handle()


async def main():
    """Start the Pipeline AudioSocket server."""
    logger.info(f"Pipeline Bridge starting on {AUDIOSOCKET_HOST}:{AUDIOSOCKET_PORT}")
    logger.info(f"Ollama: {OLLAMA_HOST} model={OLLAMA_MODEL}")
    logger.info(f"Piper: {PIPER_HOST}:{PIPER_PORT}")
    logger.info(f"Whisper: model={WHISPER_MODEL} device={WHISPER_DEVICE} compute={WHISPER_COMPUTE}")
    logger.info(f"Max concurrent calls: {MAX_CONCURRENT_CALLS}")

    # Pre-load Whisper model
    try:
        logger.info("Pre-loading Whisper model...")
        get_whisper_model()
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        logger.info("Whisper will be loaded on first call")

    server = await asyncio.start_server(
        handle_connection,
        AUDIOSOCKET_HOST,
        AUDIOSOCKET_PORT,
    )

    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    logger.info(f"Pipeline AudioSocket server listening on {addrs}")

    # Graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass  # Windows

    async with server:
        await stop_event.wait()

    logger.info("Pipeline Bridge stopped")


if __name__ == "__main__":
    asyncio.run(main())
