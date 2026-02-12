"""
Cloud Pipeline AudioSocket Bridge
===================================
Bridges Asterisk AudioSocket with Cloud AI pipeline:
  - STT: Deepgram (Nova-3), OpenAI (gpt-4o-transcribe)
  - LLM: Groq, OpenAI (GPT-4o-mini), Cerebras — all OpenAI-compatible
  - TTS: Cartesia (Sonic-3), OpenAI (tts-1), Deepgram (Aura-2)

Architecture:
    Phone → SIP Trunk → Asterisk → AudioSocket (TCP:9093)
                                          ↕
                                  Cloud Pipeline Bridge (this file)
                                    ↕        ↕         ↕
                             Cloud STT  Cloud LLM  Cloud TTS
                          (Deepgram/   (Groq/     (Cartesia/
                           OpenAI)     OpenAI/     OpenAI/
                                       Cerebras)   Deepgram)

Audio Flow:
    Asterisk (slin24 24kHz PCM16) → Cloud STT (24kHz direct)
    Transcript → Cloud LLM → response text (streaming)
    Response text → Cloud TTS (request 24kHz) → Asterisk

Requirements:
    pip install httpx numpy

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
import io
import wave
import random
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

# Cloud provider modules
from app.services.cloud_stt import cloud_transcribe, STT_PROVIDERS
from app.services.cloud_llm import cloud_llm_streaming, LLM_PROVIDER_CONFIGS
from app.services.cloud_tts import cloud_synthesize, TTS_PROVIDERS


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pipeline-bridge")


# ============================================================================
# CONFIGURATION
# ============================================================================

AUDIOSOCKET_HOST = os.environ.get("PIPELINE_AUDIOSOCKET_HOST", "0.0.0.0")
AUDIOSOCKET_PORT = int(os.environ.get("PIPELINE_AUDIOSOCKET_PORT", "9093"))

MAX_CONCURRENT_CALLS = int(os.environ.get("MAX_CONCURRENT_CALLS", "10"))

# Redis
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# PostgreSQL
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres")
DB_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME = os.environ.get("POSTGRES_DB", "voiceai")
DB_USER = os.environ.get("POSTGRES_USER", "")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")

# API Keys (from environment)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY", "")

# Default cloud providers (for filler cache and fallback)
DEFAULT_STT_PROVIDER = os.environ.get("DEFAULT_STT_PROVIDER", "deepgram")
DEFAULT_LLM_PROVIDER = os.environ.get("DEFAULT_LLM_PROVIDER", "groq")
DEFAULT_TTS_PROVIDER = os.environ.get("DEFAULT_TTS_PROVIDER", "cartesia")

# Audio constants
ASTERISK_SAMPLE_RATE = 24000   # slin24 from AudioSocket
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

# Filler phrases per language (played while AI is thinking)
FILLER_PHRASES = {
    "tr": ["Bir saniye...", "Hmm, bakıyorum...", "Anladım..."],
    "de": ["Einen Moment...", "Hmm, mal sehen...", "Verstehe..."],
    "en": ["One moment...", "Let me think...", "I see..."],
    "fr": ["Un instant...", "Voyons voir...", "Je comprends..."],
    "es": ["Un momento...", "Déjame pensar...", "Entiendo..."],
    "it": ["Un momento...", "Vediamo...", "Capisco..."],
}

# Pre-cached filler audio (populated at startup)
_filler_cache: Dict[str, List[bytes]] = {}  # {lang: [audio_24k, ...]}


# ============================================================================
# API KEY RESOLVER
# ============================================================================

def get_api_key(provider: str) -> str:
    """Resolve API key for a given provider from environment."""
    key_map = {
        "openai": OPENAI_API_KEY,
        "groq": GROQ_API_KEY,
        "cerebras": CEREBRAS_API_KEY,
        "deepgram": DEEPGRAM_API_KEY,
        "cartesia": CARTESIA_API_KEY,
    }
    return key_map.get(provider, "")


def get_tts_api_key(provider: str) -> str:
    """Get API key for TTS provider (some share keys with STT)."""
    if provider == "deepgram":
        return DEEPGRAM_API_KEY
    return get_api_key(provider)


# ============================================================================
# AUDIO UTILITIES
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
                "timestamp": datetime.utcnow().isoformat(),
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
# CALL SESSION
# ============================================================================

@dataclass
class PipelineCallSession:
    """Active call session state with cloud provider configuration."""
    call_uuid: str
    agent_config: Dict[str, Any] = field(default_factory=dict)
    language: str = "tr"

    # Cloud provider selection (per-agent configurable)
    stt_provider: str = "deepgram"
    llm_provider: str = "groq"
    tts_provider: str = "cartesia"

    # API keys (resolved from environment)
    stt_api_key: str = ""
    llm_api_key: str = ""
    tts_api_key: str = ""

    # Model selection
    stt_model: str = ""   # Empty = use provider default
    llm_model: str = ""   # Empty = use provider default
    tts_model: str = ""   # Empty = use provider default

    # Voice (TTS voice identifier for the chosen provider)
    tts_voice: str = ""

    # LLM settings
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
    Handles a single call session through the cloud pipeline.

    Flow per turn:
    1. Collect audio from Asterisk (with VAD)
    2. When silence detected → transcribe with Cloud STT
    3. Send transcript to Cloud LLM (streaming)
    4. Stream LLM response → synthesize with Cloud TTS
    5. Send TTS audio back to Asterisk
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.session: Optional[PipelineCallSession] = None
        self._running = False
        self._processing = False  # True while STT/LLM is running
        self._tts_queue: asyncio.Queue = asyncio.Queue()       # text sentences → synthesis
        self._audio_queue: asyncio.Queue = asyncio.Queue()     # synthesized audio → playback
        self._interrupt_event = asyncio.Event()
        self._process_task: Optional[asyncio.Task] = None

    async def handle(self):
        """Main call handling loop."""
        peer = self.writer.get_extra_info("peername")
        logger.info(f"New connection from {peer}")

        try:
            # Step 1: Read UUID from AudioSocket
            call_uuid = await self._read_uuid()
            if not call_uuid:
                logger.debug("No UUID received (likely healthcheck), closing connection")
                return

            logger.info(f"[{call_uuid[:8]}] Call started")

            # Step 2: Get agent config from Redis
            agent_config = await get_call_setup_from_redis(call_uuid) or {}
            language = agent_config.get("language", "tr")

            # Step 3: Resolve cloud providers (per-agent or defaults)
            stt_provider = agent_config.get("stt_provider", DEFAULT_STT_PROVIDER)
            llm_provider = agent_config.get("llm_provider", DEFAULT_LLM_PROVIDER)
            tts_provider = agent_config.get("tts_provider", DEFAULT_TTS_PROVIDER)

            # Resolve API keys
            stt_api_key = get_api_key(stt_provider)
            llm_api_key = get_api_key(llm_provider)
            tts_api_key = get_tts_api_key(tts_provider)

            # Validate API keys
            if not stt_api_key:
                logger.error(f"[{call_uuid[:8]}] No API key for STT provider '{stt_provider}'")
            if not llm_api_key:
                logger.error(f"[{call_uuid[:8]}] No API key for LLM provider '{llm_provider}'")
            if not tts_api_key:
                logger.error(f"[{call_uuid[:8]}] No API key for TTS provider '{tts_provider}'")

            # Resolve TTS voice (from agent config or language default)
            tts_voice = agent_config.get("tts_voice", "")
            if not tts_voice:
                # Use default voice for the TTS provider and language
                provider_config = TTS_PROVIDERS.get(tts_provider, {})
                default_voices = provider_config.get("default_voices", {})
                tts_voice = default_voices.get(language, "")

            # Build system prompt using the same enrichment as OpenAI Realtime
            try:
                from app.services.openai_realtime import build_system_prompt
                customer_data = None
                cust_name = agent_config.get("customer_name", "")
                if cust_name:
                    customer_data = {
                        "name": cust_name,
                        "phone": "",
                        "title": agent_config.get("customer_title", ""),
                    }
                system_prompt = build_system_prompt(agent_config, customer_data)
            except Exception as e:
                logger.warning(f"[{call_uuid[:8]}] build_system_prompt failed, using raw prompt: {e}")
                system_prompt = agent_config.get("prompt", "")
            if not system_prompt:
                system_prompt = self._build_default_prompt(language)

            self.session = PipelineCallSession(
                call_uuid=call_uuid,
                agent_config=agent_config,
                language=language,
                stt_provider=stt_provider,
                llm_provider=llm_provider,
                tts_provider=tts_provider,
                stt_api_key=stt_api_key,
                llm_api_key=llm_api_key,
                tts_api_key=tts_api_key,
                stt_model=agent_config.get("stt_model", ""),
                llm_model=agent_config.get("llm_model", ""),
                tts_model=agent_config.get("tts_model", ""),
                tts_voice=tts_voice,
                temperature=agent_config.get("temperature", 0.7),
                system_prompt=system_prompt,
                connected_at=datetime.utcnow(),
            )

            logger.info(
                f"[{call_uuid[:8]}] Cloud providers: "
                f"STT={stt_provider}, LLM={llm_provider}, TTS={tts_provider} "
                f"(voice={tts_voice}, lang={language})"
            )

            # Initialize conversation with system prompt
            self.session.conversation_history.append({
                "role": "system",
                "content": system_prompt,
            })

            self._running = True

            # Start TTS pipeline: synthesis task (text→audio) + playback task (audio→asterisk)
            synthesis_task = asyncio.create_task(self._tts_synthesis_loop())
            playback_task = asyncio.create_task(self._tts_playback_loop())

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

            # Step 4: Main audio processing loop + hangup signal checker
            hangup_task = asyncio.create_task(self._check_hangup_signal())
            try:
                await self._audio_loop()
            finally:
                hangup_task.cancel()
                try:
                    await hangup_task
                except (asyncio.CancelledError, Exception):
                    pass

        except asyncio.CancelledError:
            logger.info(f"[{self.session.call_uuid[:8] if self.session else '?'}] Call cancelled")
        except Exception as e:
            logger.error(f"Call handler error: {e}", exc_info=True)
        finally:
            self._running = False
            # Cancel any in-progress processing task
            if self._process_task and not self._process_task.done():
                self._process_task.cancel()
                try:
                    await self._process_task
                except (asyncio.CancelledError, Exception):
                    pass
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

    async def _check_hangup_signal(self):
        """Check Redis for external hangup signal (from frontend/API).
        When signal is received, send MSG_HANGUP to Asterisk and stop the call.
        """
        if not self.session:
            return
        try:
            import redis.asyncio as redis_async
            r = redis_async.from_url(REDIS_URL, decode_responses=True)
            try:
                while self._running:
                    sig = await r.get(f"hangup_signal:{self.session.call_uuid}")
                    if sig:
                        logger.info(f"[{self.session.call_uuid[:8]}] Redis hangup signal received - forcing disconnect")
                        await r.delete(f"hangup_signal:{self.session.call_uuid}")
                        self._running = False

                        # Send hangup to Asterisk so the SIP call is terminated
                        try:
                            hangup_frame = struct.pack(">BH", MSG_HANGUP, 0)
                            self.writer.write(hangup_frame)
                            await self.writer.drain()
                        except Exception:
                            pass

                        # Close TCP writer to unblock _audio_loop reader
                        try:
                            self.writer.close()
                        except Exception:
                            pass

                        break
                    await asyncio.sleep(1)
            finally:
                await r.close()
        except Exception as e:
            logger.warning(f"[{self.session.call_uuid[:8]}] Hangup signal check error: {e}")

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

                # If AI is speaking or processing STT/LLM, keep reading
                # but don't collect for VAD (keeps TCP connection alive)
                if self.session.ai_speaking or self._processing:
                    if self.session.ai_speaking:
                        energy = rms_energy(audio_data)
                        if energy > VAD_ENERGY_THRESHOLD * 2.0:
                            # User is trying to speak while AI talks → interrupt
                            self._interrupt_event.set()
                            self.session.ai_speaking = False
                            # Clear both TTS and audio queues
                            while not self._tts_queue.empty():
                                try:
                                    self._tts_queue.get_nowait()
                                except asyncio.QueueEmpty:
                                    break
                            while not self._audio_queue.empty():
                                try:
                                    self._audio_queue.get_nowait()
                                except asyncio.QueueEmpty:
                                    break
                    continue  # Don't collect audio while AI speaks/processing

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
                            # Process utterance as concurrent task
                            # This keeps audio loop alive (prevents broken pipe)
                            self._processing = True
                            self._process_task = asyncio.create_task(
                                self._process_utterance_wrapper(bytes(speech_buffer))
                            )

                        is_speaking = False
                        speech_buffer = bytearray()

            except asyncio.TimeoutError:
                # No audio for 30 seconds
                logger.info(f"[{self.session.call_uuid[:8]}] Audio timeout")
                break
            except ConnectionError:
                logger.info(f"[{self.session.call_uuid[:8]}] Connection lost")
                break

    async def _play_filler(self):
        """Play a short filler audio while AI is thinking."""
        lang = self.session.language
        cached = _filler_cache.get(lang, [])
        if not cached:
            # Generate filler on-the-fly as fallback
            phrases = FILLER_PHRASES.get(lang, FILLER_PHRASES["en"])
            phrase = random.choice(phrases)
            try:
                tts_audio, actual_rate = await cloud_synthesize(
                    text=phrase,
                    provider=self.session.tts_provider,
                    api_key=self.session.tts_api_key,
                    language=lang,
                    sample_rate=ASTERISK_SAMPLE_RATE,
                )
                if tts_audio:
                    audio_24k = resample_pcm16(tts_audio, actual_rate, ASTERISK_SAMPLE_RATE)
                    await self._send_audio_frames(audio_24k)
            except Exception as e:
                logger.debug(f"Filler TTS error: {e}")
            return

        # Use pre-cached audio
        audio_24k = random.choice(cached)
        await self._send_audio_frames(audio_24k)

    async def _send_audio_frames(self, audio_24k: bytes):
        """Send PCM audio as AudioSocket frames."""
        chunk_size = ASTERISK_SAMPLE_RATE * CHUNK_DURATION_MS // 1000 * 2  # 960 bytes
        offset = 0
        while offset < len(audio_24k) and self._running:
            chunk = audio_24k[offset:offset + chunk_size]
            if len(chunk) < chunk_size:
                chunk += b"\x00" * (chunk_size - len(chunk))
            frame = struct.pack(">BH", MSG_AUDIO_24K, len(chunk)) + chunk
            try:
                self.writer.write(frame)
                await self.writer.drain()
            except (ConnectionError, BrokenPipeError):
                self._running = False
                return
            offset += chunk_size
            await asyncio.sleep(CHUNK_DURATION_MS / 1000.0 * 0.8)

    async def _process_utterance_wrapper(self, audio_data: bytes):
        """Wrapper that ensures _processing flag is reset after processing."""
        try:
            # Play filler audio immediately so user knows AI is thinking
            await self._play_filler()
            await self._process_utterance(audio_data)
        except Exception as e:
            logger.error(f"[{self.session.call_uuid[:8]}] Utterance wrapper error: {e}", exc_info=True)
        finally:
            self._processing = False

    async def _process_utterance(self, audio_data: bytes):
        """Process a complete utterance: Cloud STT → Cloud LLM → Cloud TTS with detailed timing."""
        try:
            turn_start = time.monotonic()

            # Step 1: Transcribe with Cloud STT (send 24kHz audio directly)
            t0 = time.monotonic()
            text = await cloud_transcribe(
                pcm_data=audio_data,
                provider=self.session.stt_provider,
                api_key=self.session.stt_api_key,
                language=self.session.language,
                sample_rate=ASTERISK_SAMPLE_RATE,  # 24kHz — cloud providers handle any rate
                model=self.session.stt_model or None,
            )
            stt_time = (time.monotonic() - t0) * 1000

            if not text or len(text.strip()) < 3:
                logger.debug(f"[{self.session.call_uuid[:8]}] Too short transcription: '{text}', skipping")
                return

            logger.info(
                f"[{self.session.call_uuid[:8]}] STT [{self.session.stt_provider}] "
                f"({stt_time:.0f}ms): {text}"
            )
            self.session.total_user_messages += 1

            # Save to Redis
            await save_transcript_to_redis(self.session.call_uuid, "user", text)

            # Step 2: Add to conversation and get Cloud LLM response
            self.session.conversation_history.append({
                "role": "user",
                "content": text,
            })

            t0 = time.monotonic()
            first_sentence_time = None
            sentence_count = 0

            # Use streaming for sentence-level TTS pipelining
            full_response = ""
            sentence_buffer = ""

            async for chunk in cloud_llm_streaming(
                messages=self.session.conversation_history,
                provider=self.session.llm_provider,
                api_key=self.session.llm_api_key,
                model=self.session.llm_model or None,
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
                            sentence_count += 1
                            if first_sentence_time is None:
                                first_sentence_time = (time.monotonic() - t0) * 1000
                                logger.info(
                                    f"[{self.session.call_uuid[:8]}] LLM [{self.session.llm_provider}] "
                                    f"first sentence ({first_sentence_time:.0f}ms): "
                                    f"'{sentence[:60]}'"
                                )
                            # Queue sentence for TTS immediately
                            await self._tts_queue.put(sentence)
                            break

            # Process remaining buffer
            if sentence_buffer.strip() and len(sentence_buffer.strip()) > 3:
                sentence_count += 1
                await self._tts_queue.put(sentence_buffer.strip())

            # Signal end of response
            await self._tts_queue.put(None)

            llm_time = (time.monotonic() - t0) * 1000
            total_time = (time.monotonic() - turn_start) * 1000
            logger.info(
                f"[{self.session.call_uuid[:8]}] Turn complete: "
                f"STT={stt_time:.0f}ms [{self.session.stt_provider}], "
                f"LLM={llm_time:.0f}ms [{self.session.llm_provider}] ({sentence_count} sentences), "
                f"total={total_time:.0f}ms | {full_response[:80]}..."
            )

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

    async def _tts_synthesis_loop(self):
        """
        Background task: consume text sentences from _tts_queue,
        synthesize with Cloud TTS, put resulting audio into _audio_queue.

        Runs concurrently with _tts_playback_loop so next sentence
        is being synthesized while current sentence is playing.
        """
        while self._running:
            try:
                sentence = await asyncio.wait_for(self._tts_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if sentence is None:
                # Signal end-of-response to playback loop
                await self._audio_queue.put(None)
                continue

            if self._interrupt_event.is_set():
                # User interrupted, drain remaining text queue
                while not self._tts_queue.empty():
                    try:
                        self._tts_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                await self._audio_queue.put(None)
                continue

            try:
                # Synthesize with Cloud TTS — request 24kHz to match Asterisk
                tts_audio, actual_rate = await cloud_synthesize(
                    text=sentence,
                    provider=self.session.tts_provider,
                    api_key=self.session.tts_api_key,
                    voice=self.session.tts_voice or None,
                    language=self.session.language,
                    model=self.session.tts_model or None,
                    sample_rate=ASTERISK_SAMPLE_RATE,
                )

                if not tts_audio:
                    logger.warning(f"[{self.session.call_uuid[:8]}] TTS returned empty audio")
                    continue

                # Resample if TTS returned a different sample rate
                if actual_rate != ASTERISK_SAMPLE_RATE:
                    t0 = time.monotonic()
                    audio_24k = resample_pcm16(tts_audio, actual_rate, ASTERISK_SAMPLE_RATE)
                    resample_time = (time.monotonic() - t0) * 1000
                    if resample_time > 5:
                        logger.debug(
                            f"[{self.session.call_uuid[:8]}] Resample {actual_rate}→{ASTERISK_SAMPLE_RATE}: "
                            f"{resample_time:.0f}ms ({len(tts_audio)}→{len(audio_24k)} bytes)"
                        )
                else:
                    audio_24k = tts_audio

                # Put ready-to-play audio into playback queue
                await self._audio_queue.put(audio_24k)

            except Exception as e:
                logger.error(f"[{self.session.call_uuid[:8]}] TTS synthesis error: {e}")

    async def _tts_playback_loop(self):
        """
        Background task: consume pre-synthesized audio from _audio_queue
        and send to Asterisk as AudioSocket frames.

        Separated from synthesis so next sentence can be synthesizing
        while current one plays — eliminates inter-sentence gaps.
        """
        while self._running:
            try:
                audio_24k = await asyncio.wait_for(self._audio_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if audio_24k is None:
                self.session.ai_speaking = False
                continue

            try:
                self.session.ai_speaking = True
                self._interrupt_event.clear()

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
                    # Drain remaining audio queue
                    while not self._audio_queue.empty():
                        try:
                            self._audio_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    # Also drain text queue
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


async def _precache_filler_audio():
    """Pre-generate filler audio for all languages at startup using Cloud TTS."""
    global _filler_cache

    tts_provider = DEFAULT_TTS_PROVIDER
    tts_api_key = get_tts_api_key(tts_provider)

    if not tts_api_key:
        logger.warning(
            f"No API key for default TTS provider '{tts_provider}', "
            f"filler audio will be generated on-the-fly during calls"
        )
        return

    logger.info(f"Pre-caching filler audio using {tts_provider}...")

    provider_config = TTS_PROVIDERS.get(tts_provider, {})
    default_voices = provider_config.get("default_voices", {})

    for lang, phrases in FILLER_PHRASES.items():
        voice = default_voices.get(lang, "")
        cached_list = []
        for phrase in phrases:
            try:
                tts_audio, actual_rate = await cloud_synthesize(
                    text=phrase,
                    provider=tts_provider,
                    api_key=tts_api_key,
                    voice=voice,
                    language=lang,
                    sample_rate=ASTERISK_SAMPLE_RATE,
                )
                if tts_audio and len(tts_audio) > 100:
                    audio_24k = resample_pcm16(tts_audio, actual_rate, ASTERISK_SAMPLE_RATE)
                    cached_list.append(audio_24k)
                    logger.debug(f"Cached filler [{lang}]: '{phrase}' ({len(audio_24k)} bytes)")
            except Exception as e:
                logger.warning(f"Failed to cache filler [{lang}] '{phrase}': {e}")

        if cached_list:
            _filler_cache[lang] = cached_list
            logger.info(f"Cached {len(cached_list)} filler phrases for [{lang}]")
        else:
            logger.warning(f"No filler audio cached for [{lang}]")

    logger.info(
        f"Filler cache complete: {sum(len(v) for v in _filler_cache.values())} phrases "
        f"across {len(_filler_cache)} languages"
    )


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
    """Start the Cloud Pipeline AudioSocket server."""
    logger.info(f"Cloud Pipeline Bridge starting on {AUDIOSOCKET_HOST}:{AUDIOSOCKET_PORT}")
    logger.info(f"Default STT: {DEFAULT_STT_PROVIDER}")
    logger.info(f"Default LLM: {DEFAULT_LLM_PROVIDER}")
    logger.info(f"Default TTS: {DEFAULT_TTS_PROVIDER}")
    logger.info(f"Max concurrent calls: {MAX_CONCURRENT_CALLS}")

    # Log available API keys (without exposing values)
    available_keys = []
    for name, key in [
        ("OpenAI", OPENAI_API_KEY),
        ("Groq", GROQ_API_KEY),
        ("Cerebras", CEREBRAS_API_KEY),
        ("Deepgram", DEEPGRAM_API_KEY),
        ("Cartesia", CARTESIA_API_KEY),
    ]:
        if key:
            available_keys.append(name)
    logger.info(f"Available API keys: {', '.join(available_keys) or 'NONE'}")

    if not available_keys:
        logger.error(
            "No API keys configured! Set at least one of: "
            "OPENAI_API_KEY, GROQ_API_KEY, CEREBRAS_API_KEY, "
            "DEEPGRAM_API_KEY, CARTESIA_API_KEY"
        )

    # Pre-cache filler audio for all languages
    await _precache_filler_audio()

    server = await asyncio.start_server(
        handle_connection,
        AUDIOSOCKET_HOST,
        AUDIOSOCKET_PORT,
    )

    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    logger.info(f"Cloud Pipeline AudioSocket server listening on {addrs}")

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

    logger.info("Cloud Pipeline Bridge stopped")


if __name__ == "__main__":
    asyncio.run(main())
