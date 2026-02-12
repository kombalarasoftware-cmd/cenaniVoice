"""
Asterisk AudioSocket ↔ OpenAI Realtime Mini Bridge (v4 - Native 24kHz)
========================================================================
Receives calls from Asterisk via AudioSocket protocol and
bridges them to OpenAI Realtime Mini WebSocket.

*** 24kHz PCM16 PASSTHROUGH ***
Uses chan_audiosocket with 24kHz slin24 (0x13).
OpenAI Realtime expects 24kHz PCM16.
No resampling - direct passthrough.

Architecture:
    Phone → SIP Trunk → Asterisk → AudioSocket (TCP:9092)
                                          ↕
                                  This Python Server (passthrough)
                                          ↕
                                    OpenAI Realtime API (WSS)

Audio Flow (v4 - Native 24kHz):
    Asterisk (slin24) → 24kHz PCM16 → OpenAI Realtime
    OpenAI Realtime → 24kHz PCM16 → Asterisk (slin24)

Requirements:
    pip install websockets

Asterisk Dialplan:
    Dial(AudioSocket/host:port/${UUID}/c(slin24))

Asterisk extensions.conf:
    [ai-agent]
    exten => 5001,1,Answer()
    exten => 5001,n,Set(UUID=${SHELL(cat /proc/sys/kernel/random/uuid | tr -d '\\n')})
    exten => 5001,n,Dial(AudioSocket/127.0.0.1:9092/${UUID}/c(slin24))
    exten => 5001,n,Hangup()

Usage:
    OPENAI_API_KEY=sk-xxx python asterisk_realtime_bridge.py

Cenani - MUTLU TELEKOM | 2026
"""

import asyncio
import json
import os
import sys
import base64
import struct
import uuid
import time
import logging
import signal
import socket
from typing import Optional, Dict, Any
from datetime import datetime

try:
    # websockets 16.x asyncio API
    from websockets.asyncio.client import connect as ws_connect
    from websockets.asyncio.client import ClientConnection
    from websockets.protocol import State  # for state checking
    import websockets.exceptions
except ImportError:
    print("❌ websockets required: pip install websockets")
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    print("❌ aiohttp required: pip install aiohttp")
    sys.exit(1)

try:
    import asyncpg
except ImportError:
    print("❌ asyncpg required: pip install asyncpg")
    sys.exit(1)



# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("asterisk-realtime-bridge")

# ============================================================================
# CONFIGURATION
# ============================================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
MODEL = os.environ.get("REALTIME_MODEL", "gpt-realtime-mini")

# Google Gemini (Vertex AI) settings
GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
GOOGLE_PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID", "")
GOOGLE_LOCATION = os.environ.get("GOOGLE_LOCATION", "us-central1")
GEMINI_DEFAULT_MODEL = "gemini-live-2.5-flash-native-audio"

# AudioSocket server ayarları
AUDIOSOCKET_HOST = os.environ.get("AUDIOSOCKET_HOST", "0.0.0.0")
AUDIOSOCKET_PORT = int(os.environ.get("AUDIOSOCKET_PORT", "9092"))
AUDIOSOCKET_BIND_HOST = os.environ.get("AUDIOSOCKET_BIND_HOST", "").strip()
LOCAL_BIND_HOSTS = {"0.0.0.0", "127.0.0.1", "::", "::1", "localhost"}

# Asterisk ARI ayarları (channel variables için)
ARI_HOST = os.environ.get("ASTERISK_HOST", "asterisk")
ARI_PORT = int(os.environ.get("ASTERISK_ARI_PORT", "8088"))
ARI_USERNAME = os.environ.get("ASTERISK_ARI_USER", "")
ARI_PASSWORD = os.environ.get("ASTERISK_ARI_PASSWORD", "")

# PostgreSQL ayarları (agent bilgileri için)
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres")
DB_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME = os.environ.get("POSTGRES_DB", "voiceai")
DB_USER = os.environ.get("POSTGRES_USER", "")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")

# Redis ayarları (call setup bilgileri için)
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

if AUDIOSOCKET_BIND_HOST:
    AUDIOSOCKET_BIND = AUDIOSOCKET_BIND_HOST
elif AUDIOSOCKET_HOST in LOCAL_BIND_HOSTS:
    AUDIOSOCKET_BIND = AUDIOSOCKET_HOST
else:
    AUDIOSOCKET_BIND = "0.0.0.0"

# Eşzamanlı çağrı limiti
MAX_CONCURRENT_CALLS = int(os.environ.get("MAX_CONCURRENT_CALLS", "50"))

# OpenAI Realtime API Pricing (per token)
# https://openai.com/api/pricing/
COST_PER_TOKEN = {
    "gpt-realtime": {
        "input_text": 4.00 / 1_000_000,
        "input_audio": 32.00 / 1_000_000,
        "cached_input_text": 0.40 / 1_000_000,
        "cached_input_audio": 0.40 / 1_000_000,
        "output_text": 16.00 / 1_000_000,
        "output_audio": 64.00 / 1_000_000,
    },
    "gpt-realtime-mini": {
        "input_text": 0.60 / 1_000_000,
        "input_audio": 10.00 / 1_000_000,
        "cached_input_text": 0.06 / 1_000_000,
        "cached_input_audio": 0.30 / 1_000_000,
        "output_text": 2.40 / 1_000_000,
        "output_audio": 20.00 / 1_000_000,
    },
}

# xAI Grok Voice Agent Pricing (per minute flat rate)
XAI_COST_PER_MINUTE = 0.10  # $0.10/min estimated (xAI per-minute billing)

# Google Gemini Live API Pricing (per 1M tokens)
GEMINI_COST_PER_TOKEN = {
    "input_audio": 3.00 / 1_000_000,
    "output_audio": 12.00 / 1_000_000,
}

# OpenAI WebSocket URL
OPENAI_WS_URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"

# xAI WebSocket URL (model is sent in session config, not URL)
XAI_WS_URL = "wss://api.x.ai/v1/realtime"

# Gemini Vertex AI WebSocket URL template
# Format: wss://{LOCATION}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent
# Gemini Vertex AI WebSocket URL template
# Format: wss://{LOCATION}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent
GEMINI_WS_URL_TEMPLATE = "wss://{location}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent"


# ============================================================================
# GEMINI VERTEX AI - OAuth2 Token Management
# ============================================================================

_gemini_credentials = None
_gemini_token_cache: dict = {"token": None, "expiry": 0}


def _get_gemini_access_token() -> str:
    """
    Get a valid OAuth2 access token for Vertex AI from service account JSON.
    Caches the token and refreshes when expired.
    Uses google-auth library for service account authentication.
    """
    global _gemini_credentials

    # Check cache first
    if _gemini_token_cache["token"] and time.time() < _gemini_token_cache["expiry"] - 60:
        return _gemini_token_cache["token"]

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        if _gemini_credentials is None:
            sa_file = GOOGLE_SERVICE_ACCOUNT_FILE
            if not sa_file or not os.path.exists(sa_file):
                raise FileNotFoundError(
                    f"Google service account file not found: {sa_file}. "
                    "Set GOOGLE_SERVICE_ACCOUNT_FILE environment variable."
                )
            _gemini_credentials = service_account.Credentials.from_service_account_file(
                sa_file,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        # Refresh the token
        _gemini_credentials.refresh(Request())

        _gemini_token_cache["token"] = _gemini_credentials.token
        # Token typically expires in 3600s; store expiry
        if _gemini_credentials.expiry:
            _gemini_token_cache["expiry"] = _gemini_credentials.expiry.timestamp()
        else:
            _gemini_token_cache["expiry"] = time.time() + 3500

        logger.info("🔑 Gemini OAuth2 token refreshed successfully")
        return _gemini_credentials.token

    except ImportError:
        raise ImportError(
            "google-auth package is required for Gemini provider. "
            "Install it with: pip install google-auth"
        )
    except Exception as e:
        logger.error(f"❌ Gemini OAuth2 token error: {e}")
        raise

# ============================================================================
# ASTERISK HANGUP CAUSE → SIP CODE MAPPING
# ============================================================================
# Maps common Asterisk hangup cause strings to standard SIP response codes.
# Reference: https://wiki.asterisk.org/wiki/display/AST/Hangup+Cause+Mappings
HANGUP_CAUSE_TO_SIP = {
    "Normal Clearing": 200,
    "User Busy": 486,
    "No Answer": 480,
    "Call Rejected": 403,
    "Number Changed": 410,
    "Normal Unspecified": 200,
    "No Route": 404,
    "No Route To Destination": 404,
    "Channel Unacceptable": 406,
    "Destination Out Of Order": 502,
    "Invalid Number Format": 484,
    "Facility Rejected": 501,
    "Normal Circuit Congestion": 503,
    "Network Out Of Order": 503,
    "Temporary Failure": 503,
    "Switch Congestion": 503,
    "Requested Channel Unavailable": 503,
    "Resource Unavailable": 503,
    "Facility Not Subscribed": 403,
    "Service Unavailable": 503,
    "Bearercapability Not Available": 503,
    "Bearercapability Not Implemented": 501,
    "Interworking": 500,
    "Subscriber Absent": 480,
    "Agent End Call": 200,
    "User Hangup (Manual)": 200,
    "orphan_cleanup": 500,
}


def hangup_cause_to_sip_code(cause: str) -> int:
    """Convert Asterisk hangup cause string to SIP response code."""
    if not cause:
        return 200
    return HANGUP_CAUSE_TO_SIP.get(cause, 500)

# Title translations (centralized in prompt_constants)
from app.services.prompt_constants import TITLE_AFTER_NAME, TITLE_TRANSLATIONS

# ============================================================================
# AUDIO FORMAT CONSTANTS - Native 24kHz Passthrough
# ============================================================================
# Asterisk Dial(AudioSocket/.../c(slin24)) = 24kHz slin (0x13)
# OpenAI Realtime = 24kHz PCM16
# Resampling yok

ASTERISK_SAMPLE_RATE = 24000                 # slin24 with Dial(AudioSocket/.../c(slin24))
OPENAI_SAMPLE_RATE = 24000                   # OpenAI requirement
CHUNK_DURATION_MS = 20                       # 20ms chunk

# 24kHz chunk: 24kHz * 0.020s * 2 bytes = 960 bytes
ASTERISK_CHUNK_BYTES = ASTERISK_SAMPLE_RATE * CHUNK_DURATION_MS // 1000 * 2  # 960

# OpenAI chunk: 24kHz * 0.020s * 2 bytes = 960 bytes
OPENAI_CHUNK_BYTES = OPENAI_SAMPLE_RATE * CHUNK_DURATION_MS // 1000 * 2  # 960

# AudioSocket protokol sabitleri
MSG_HANGUP = 0x00
MSG_UUID   = 0x01
MSG_DTMF   = 0x03
MSG_AUDIO_8K  = 0x10   # 8kHz slin (fallback)
MSG_AUDIO_16K = 0x12   # 16kHz slin
MSG_AUDIO_24K = 0x13   # 24kHz slin ← BİZİM KULLANIMIZ
MSG_AUDIO_48K = 0x16   # 48kHz slin
MSG_ERROR  = 0xFF

# Kabul edilen audio mesaj tipleri (8kHz fallback dahil)
AUDIO_MSG_TYPES = {MSG_AUDIO_8K, MSG_AUDIO_16K, MSG_AUDIO_24K, MSG_AUDIO_48K}


# ============================================================================
# REDIS - CALL SETUP LOOKUP
# ============================================================================

async def save_transcript_to_redis(call_uuid: str, role: str, content: str) -> bool:
    """
    Transcript'i Redis'e kaydet (gerçek zamanlı).
    Frontend polling ile bu veriyi alabilir.
    """
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
            # LPUSH ile listenin başına ekle
            await r.lpush(transcript_key, message)
            # 1 saat TTL
            await r.expire(transcript_key, 3600)
            logger.debug(f"[{call_uuid[:8]}] 📝 Transcript kaydedildi: {role}")
            return True
        finally:
            await r.close()
    except Exception as e:
        logger.warning(f"[{call_uuid[:8]}] ⚠️ Transcript kaydetme hatası: {e}")
    return False


async def get_call_setup_from_redis(call_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Redis'ten call setup bilgilerini al.
    Backend outbound_calls.py tarafından kaydedilen agent ayarları.
    """
    try:
        import redis.asyncio as redis_async
        r = redis_async.from_url(REDIS_URL, decode_responses=True)
        try:
            data = await r.get(f"call_setup:{call_uuid}")
            if data:
                result = json.loads(data)
                logger.info(f"[{call_uuid[:8]}] ✅ Redis'ten agent ayarları bulundu: agent_id={result.get('agent_id')}")
                return result
            else:
                logger.info(f"[{call_uuid[:8]}] ℹ️ Redis'te call setup bulunamadı (inbound çağrı olabilir)")
        finally:
            await r.close()
    except Exception as e:
        logger.warning(f"[{call_uuid[:8]}] ⚠️ Redis lookup hatası: {e}")
    
    return None


async def publish_event_to_redis(call_uuid: str, event: Dict[str, Any]) -> bool:
    """
    OpenAI event'ini Redis pub/sub kanalına yayınla.
    Frontend SSE ile bu kanalı dinler.
    """
    try:
        import redis.asyncio as redis_async
        r = redis_async.from_url(REDIS_URL, decode_responses=True)
        try:
            channel = f"call_events:{call_uuid}"
            event_data = json.dumps({
                **event,
                "call_id": call_uuid,
                "server_timestamp": datetime.utcnow().isoformat()
            })
            await r.publish(channel, event_data)
            return True
        finally:
            await r.close()
    except Exception as e:
        logger.warning(f"[{call_uuid[:8]}] ⚠️ Event publish hatası: {e}")
    return False


async def save_usage_to_redis(call_uuid: str, usage: Dict[str, Any], model: str = "gpt-realtime-mini") -> bool:
    """
    Token kullanım bilgisini Redis'e kaydet (cost hesaplama için).
    Her response.done event'inde güncellenir.
    """
    try:
        import redis.asyncio as redis_async
        r = redis_async.from_url(REDIS_URL, decode_responses=True)
        try:
            usage_key = f"call_usage:{call_uuid}"
            
            # Mevcut kullanımı al
            existing = await r.get(usage_key)
            if existing:
                existing_data = json.loads(existing)
                # Toplam token sayılarını biriktir
                usage["input_tokens"] = existing_data.get("input_tokens", 0) + usage.get("input_tokens", 0)
                usage["output_tokens"] = existing_data.get("output_tokens", 0) + usage.get("output_tokens", 0)
                
                # Token detaylarını biriktir
                if "input_token_details" in usage and "input_token_details" in existing_data:
                    for key in ["text_tokens", "audio_tokens", "cached_tokens"]:
                        usage["input_token_details"][key] = (
                            existing_data["input_token_details"].get(key, 0) + 
                            usage.get("input_token_details", {}).get(key, 0)
                        )
                
                if "output_token_details" in usage and "output_token_details" in existing_data:
                    for key in ["text_tokens", "audio_tokens"]:
                        usage["output_token_details"][key] = (
                            existing_data["output_token_details"].get(key, 0) + 
                            usage.get("output_token_details", {}).get(key, 0)
                        )
            
            usage["model"] = model
            usage["updated_at"] = datetime.utcnow().isoformat()
            
            await r.set(usage_key, json.dumps(usage))
            await r.expire(usage_key, 86400)  # 24 saat TTL
            return True
        finally:
            await r.close()
    except Exception as e:
        logger.warning(f"[{call_uuid[:8]}] ⚠️ Usage kaydetme hatası: {e}")
    return False


async def save_audio_to_redis(call_uuid: str, audio_data: bytes, channel: str = "output") -> bool:
    """
    Audio buffer'ı Redis'e ekle (recording için).
    Mevcut audio'ya append eder.
    channel: "output" (agent/AI sesi) veya "input" (müşteri sesi)
    """
    try:
        import redis.asyncio as redis_async
        r = redis_async.from_url(REDIS_URL, decode_responses=False)
        try:
            audio_key = f"call_audio_{channel}:{call_uuid}"
            # Append audio data
            await r.append(audio_key, audio_data)
            # 1 saat TTL (her ekleme TTL'i sıfırlar)
            await r.expire(audio_key, 3600)
            return True
        finally:
            await r.close()
    except Exception as e:
        logger.warning(f"[{call_uuid[:8]}] ⚠️ Audio kaydetme hatası ({channel}): {e}")
    return False


# ============================================================================
# DATABASE - AGENT SETTINGS
# ============================================================================

async def get_agent_from_db(agent_id: int) -> Optional[Dict[str, Any]]:
    """
    PostgreSQL'den agent bilgilerini çek.
    """
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        
        try:
            row = await conn.fetchrow(
                """SELECT id, name, voice, model_type, language, provider, timezone,
                          prompt_role, prompt_personality, prompt_context,
                          prompt_pronunciations, prompt_sample_phrases,
                          prompt_flow, prompt_rules, prompt_safety,
                          prompt_language, prompt_tools, knowledge_base,
                          greeting_message, first_speaker,
                          transcript_model, temperature, vad_threshold,
                          silence_duration_ms, prefix_padding_ms,
                          turn_detection, vad_eagerness, max_output_tokens,
                          noise_reduction, interrupt_response, create_response
                   FROM agents WHERE id = $1""",
                agent_id
            )

            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "voice": row["voice"] or "ash",
                    "model_type": row["model_type"] or "gpt-realtime-mini",
                    "language": row["language"] or "tr",
                    "provider": row.get("provider") or "openai",
                    "timezone": row.get("timezone") or "Europe/Istanbul",
                    # Individual prompt fields for PromptBuilder
                    "prompt_role": row.get("prompt_role") or "",
                    "prompt_personality": row.get("prompt_personality") or "",
                    "prompt_context": row.get("prompt_context") or "",
                    "prompt_pronunciations": row.get("prompt_pronunciations") or "",
                    "prompt_sample_phrases": row.get("prompt_sample_phrases") or "",
                    "prompt_flow": row.get("prompt_flow") or "",
                    "prompt_rules": row.get("prompt_rules") or "",
                    "prompt_safety": row.get("prompt_safety") or "",
                    "prompt_language": row.get("prompt_language") or "",
                    "prompt_tools": row.get("prompt_tools") or "",
                    "knowledge_base": row.get("knowledge_base") or "",
                    "greeting_message": row.get("greeting_message") or "",
                    "first_speaker": row.get("first_speaker") or "agent",
                    "transcript_model": row["transcript_model"] or "gpt-4o-transcribe",
                    "temperature": row["temperature"] or 0.6,
                    "vad_threshold": row["vad_threshold"] or 0.5,
                    "silence_duration_ms": row["silence_duration_ms"] or 1000,
                    "prefix_padding_ms": row["prefix_padding_ms"] or 400,
                    "turn_detection": row["turn_detection"] or "semantic_vad",
                    "vad_eagerness": row["vad_eagerness"] or "low",
                    "max_output_tokens": row["max_output_tokens"] or 500,
                    "noise_reduction": row["noise_reduction"] if row["noise_reduction"] is not None else True,
                    "interrupt_response": row["interrupt_response"] if row["interrupt_response"] is not None else True,
                    "create_response": row["create_response"] if row["create_response"] is not None else True,
                }
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Database error: {e}")
    
    return None


async def get_channel_variables(call_uuid: str) -> Dict[str, str]:
    """
    Asterisk ARI API'den channel variables'ı al.
    VOICEAI_AGENT_ID ve VOICEAI_CUSTOMER_NAME için kullanılır.
    """
    variables = {}
    try:
        ari_url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels"
        auth = aiohttp.BasicAuth(ARI_USERNAME, ARI_PASSWORD)
        
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(ari_url) as response:
                if response.status == 200:
                    channels = await response.json()
                    
                    # UUID ile channel bul
                    for channel in channels:
                        channel_id = channel.get("id", "")
                        if call_uuid in channel_id or call_uuid in channel.get("name", ""):
                            # Channel variables endpoint'i
                            var_url = f"{ari_url}/{channel_id}/variable"
                            
                            # Sadece agent_id ve customer_name al
                            var_names = ["VOICEAI_AGENT_ID", "VOICEAI_CUSTOMER_NAME"]
                            
                            for var_name in var_names:
                                try:
                                    async with session.get(f"{var_url}?variable={var_name}") as var_response:
                                        if var_response.status == 200:
                                            data = await var_response.json()
                                            value = data.get("value")
                                            if value:
                                                variables[var_name] = value
                                except Exception:
                                    pass
                            
                            logger.info(f"[{call_uuid[:8]}] 📋 Channel variables: {variables}")
                            break
    except Exception as e:
        logger.warning(f"[{call_uuid[:8]}] ⚠️ ARI variables alınamadı: {e}")
    
    return variables


# ============================================================================
# SYSTEM PROMPT - Fallback prompt when no agent config is available
# ============================================================================

SYSTEM_INSTRUCTIONS = """
# Role

You are a friendly and professional customer service voice agent for MUTLU TELEKOM.
You are patient, methodical, and focused on collecting accurate customer information.
You speak clearly and concisely, adapting to the customer's pace.

# Environment

You are assisting customers via phone call.
Customers are calling to register or update their information.
You have access to data collection tools for saving customer details.

# Tone

Keep responses clear and concise (1-2 sentences per turn). This step is important.
Use a warm, professional tone with brief affirmations ("Anladım", "Tamam", "Tamamdır").
Never repeat the same phrase twice—vary your acknowledgments.
Speak in Turkish only. Never respond in another language. This step is important.

# Goal

Collect and verify customer information through this workflow:

1. Greet the customer warmly and state purpose
2. Collect full name → verify by repeating back → get confirmation
3. Collect phone number → verify digit by digit → get confirmation
4. Collect email → verify by spelling out → get confirmation
5. Collect address → verify by summarizing → get confirmation
6. Summarize all collected information
7. Thank the customer and close

This step is important: Never proceed to the next step without explicit customer confirmation.

# Guardrails

Never skip identity verification steps. This step is important.
Never guess or assume information—always ask the customer to repeat if unclear.
Never share customer data or reveal information from previous calls.
Never continue if the customer refuses to provide information—offer to call back.
If the customer becomes frustrated, remain calm and offer to transfer to a human agent.
Acknowledge when you don't understand something instead of guessing.

# Tools

## `save_customer_name`

**When to use:** After the customer confirms their name
**Parameters:**
- `first_name` (required): Customer's first name
- `last_name` (required): Customer's last name
- `confirmed` (required): Must be true—only call after customer confirmation

**Usage:**
1. Ask: "Adınızı ve soyadınızı alabilir miyim?"
2. Repeat back: "Adınız [X] [Y], doğru mu?"
3. Wait for confirmation, then call this tool

**Error handling:**
If the customer says no, ask them to repeat their name.

## `save_phone_number`

**When to use:** After the customer confirms their phone number
**Parameters:**
- `phone_number` (required): Digits only, e.g. "05321234567"
- `confirmed` (required): Must be true

**Usage:**
1. Ask: "Telefon numaranızı alabilir miyim?"
2. Repeat digit by digit: "sıfır-beş-üç-iki-bir-iki-üç-dört-beş-altı-yedi, doğru mu?"
3. Wait for confirmation, then call this tool

**Error handling:**
If the number has wrong digit count, ask customer to verify and repeat.

## `save_email`

**When to use:** After the customer confirms their email
**Parameters:**
- `email` (required): Email in written format, lowercase
- `confirmed` (required): Must be true

**Usage:**
1. Ask: "E-posta adresinizi alabilir miyim?"
2. Spell out: "a-h-m-e-t et işareti gmail nokta com, doğru mu?"
3. Wait for confirmation, then call this tool

## `save_address`

**When to use:** After the customer confirms their address
**Parameters:**
- `city` (required): City name
- `district` (required): District name
- `neighborhood`, `street`, `building_no`, `apartment_no` (optional)
- `confirmed` (required): Must be true

## `complete_registration`

**When to use:** After all information is collected and verified
**Parameters:**
- `summary` (required): Full summary of collected information

## `transfer_to_human`

**When to use:** Customer requests human agent, or issue cannot be resolved after 2 attempts
**Parameters:**
- `reason` (required): Why the transfer is needed
- `department` (optional): Target department

# Instructions

When collecting email addresses:
- Spoken: "ahmet et işareti gmail nokta com"
- Written: "ahmet@gmail.com"
- Convert "et işareti" → "@", "nokta" → "."

When collecting phone numbers:
- Spoken: "sıfır beş üç iki bir iki üç dört beş altı yedi"
- Written: "05321234567"
- Read back digit by digit with dashes between groups

# Conversation Flow

If any tool call fails:
1. Acknowledge: "Bir saniye, bilgiyi kaydederken sorun yaşıyorum."
2. Do not guess or make up information
3. Retry once, then offer alternatives
4. If error persists: "Sizi yetkili birime aktarayım, bir saniye lütfen."

# Safety & Escalation

- If the customer makes threats or uses abusive language, stay calm, warn once, then end the call politely
- If the customer reports a security concern, transfer to a human agent immediately
- Never share internal system details or customer data from other calls
- After 2 failed resolution attempts, transfer to a human operator

# Language

- Speak in Turkish only. Never switch to another language unless explicitly requested.
- Use formal register ("siz" form) by default.
"""

# ============================================================================
# TOOL DEFINITIONS — imported from universal tool registry
# ============================================================================
# The hardcoded TOOLS list has been replaced by the central tool_registry.
# Use to_openai_tools(agent_config) to get OpenAI-format tools at runtime.
# The bridge calls _build_tools() during session setup to resolve them.

from app.services.tool_registry import to_openai_tools as _registry_to_openai_tools
from app.services.tool_registry import to_gemini_tools as _registry_to_gemini_tools
from app.core.voice_config import OPENAI_VALID_VOICES
from app.core.voice_config import XAI_VALID_VOICES
from app.core.voice_config import GEMINI_VALID_VOICES

def _build_tools(agent_config: dict | None = None) -> list[dict]:
    """Build OpenAI-format tools from the universal tool registry."""
    return _registry_to_openai_tools(agent_config or {})


def _build_gemini_tools(agent_config: dict | None = None) -> list[dict]:
    """Build Gemini-format tools from the universal tool registry."""
    return _registry_to_gemini_tools(agent_config or {})

# ============================================================================
# AUDIOSOCKET PROTOKOLÜ
# ============================================================================

async def read_audiosocket_message(reader: asyncio.StreamReader):
    """
    AudioSocket protokolünden bir mesaj oku.

    Protokol formatı (her paket):
    - 1 byte: mesaj tipi
    - 2 bytes: payload uzunluğu (big-endian uint16)
    - N bytes: payload

    Mesaj tipleri:
      0x00 = Hangup (terminate)
      0x01 = UUID (16-byte binary, bağlantı başında)
      0x03 = DTMF (1 byte ASCII)
      0x10 = Audio 8kHz slin
      0x12 = Audio 16kHz slin
      0x13 = Audio 24kHz slin  ← BİZİM KULLANIMIZ
      0x16 = Audio 48kHz slin
      0xFF = Error
    """
    header = await reader.readexactly(3)
    msg_type = header[0]
    payload_length = struct.unpack("!H", header[1:3])[0]

    payload = b""
    if payload_length > 0:
        payload = await reader.readexactly(payload_length)

    return msg_type, payload


def build_audiosocket_message(msg_type: int, payload: bytes = b"") -> bytes:
    """
    AudioSocket protokolüne uygun mesaj oluştur.
    Format: [type:1byte][length:2bytes big-endian][payload:N bytes]
    """
    header = struct.pack("!BH", msg_type, len(payload))
    return header + payload


# ============================================================================
# TOOL HANDLER
# ============================================================================

active_calls: Dict[str, dict] = {}


def handle_tool_call(call_id: str, function_name: str, arguments: dict) -> str:
    """
    Tool call sonuçlarını işle.

    ENTEGRASYON NOKTASI:
    - n8n webhook: POST http://n8n.mutlutelekom.com/webhook/voice-agent
    - Django API:  POST http://api.mutlutelekom.com/api/customers/
    - Sippy Softswitch CDR eşleştirme
    """
    call_data = active_calls.get(call_id, {})
    customer = call_data.setdefault("customer", {})

    if function_name == "save_customer_name":
        if arguments.get("confirmed"):
            customer["name"] = f"{arguments.get('first_name', '')} {arguments.get('last_name', '')}"
            logger.info(f"[{call_id[:8]}] ✅ İsim: {customer['name']}")
            return json.dumps({"status": "success", "message": f"İsim kaydedildi: {customer['name']}"})
        return json.dumps({"status": "pending", "message": "Onay alınmadı, tekrar teyit et"})

    elif function_name == "save_phone_number":
        phone = "".join(c for c in arguments.get("phone_number", "") if c.isdigit())
        if len(phone) < 10 or len(phone) > 11:
            logger.warning(f"[{call_id[:8]}] ⚠️ Geçersiz numara: {phone}")
            return json.dumps({"status": "error", "message": f"Numara {len(phone)} haneli, 10-11 haneli olmalı. Tekrar sor."})
        if arguments.get("confirmed"):
            customer["phone"] = phone
            logger.info(f"[{call_id[:8]}] ✅ Telefon: {phone}")
            return json.dumps({"status": "success", "message": f"Telefon kaydedildi: {phone}"})
        return json.dumps({"status": "pending", "message": "Onay alınmadı, rakam rakam tekrarla"})

    elif function_name == "save_email":
        email = arguments.get("email", "").lower().strip()
        if "@" not in email or "." not in email:
            return json.dumps({"status": "error", "message": "E-mail geçersiz. Tekrar sor."})
        if arguments.get("confirmed"):
            customer["email"] = email
            logger.info(f"[{call_id[:8]}] ✅ Email: {email}")
            return json.dumps({"status": "success", "message": f"E-mail kaydedildi: {email}"})
        return json.dumps({"status": "pending", "message": "Onay alınmadı, harf harf spell et"})

    elif function_name == "save_address":
        if arguments.get("confirmed"):
            parts = [arguments.get(k, "") for k in
                     ["neighborhood", "street", "building_no", "apartment_no", "district", "city"]
                     if arguments.get(k)]
            customer["address"] = ", ".join(parts)
            logger.info(f"[{call_id[:8]}] ✅ Adres: {customer['address']}")
            return json.dumps({"status": "success", "message": "Adres kaydedildi"})
        return json.dumps({"status": "pending", "message": "Onay alınmadı, adresi özetle"})

    elif function_name == "complete_registration":
        logger.info(f"[{call_id[:8]}] 📋 KAYIT TAMAMLANDI: {json.dumps(customer, ensure_ascii=False)}")
        # ---- ENTEGRASYON ----
        # asyncio.create_task(notify_n8n(customer))
        # asyncio.create_task(save_to_django(customer))
        return json.dumps({"status": "success", "message": "Kayıt tamamlandı"})

    elif function_name == "transfer_to_human":
        reason = arguments.get("reason", "")
        dept = arguments.get("department", "destek")
        logger.info(f"[{call_id[:8]}] 🔄 Transfer: {dept} - {reason}")
        call_data["transfer_requested"] = True
        call_data["transfer_department"] = dept
        return json.dumps({"status": "success", "message": f"{dept} birimine aktarılıyor"})

    elif function_name == "schedule_callback":
        if not arguments.get("confirmed"):
            return json.dumps({"status": "pending", "message": "Müşteri tarih/saati henüz onaylamadı. Teyit al."})
        date_str = arguments.get("date", "")
        time_str = arguments.get("time", "")
        reason = arguments.get("reason", "")
        notes = arguments.get("notes", "")
        call_data["callback_scheduled"] = f"{date_str} {time_str}"
        call_data["callback_reason"] = reason
        call_data["callback_notes"] = notes
        logger.info(f"[{call_id[:8]}] 📅 Callback: {date_str} {time_str} - {reason}")
        return json.dumps({"status": "success", "message": f"Geri arama planlandı: {date_str} saat {time_str}"})

    elif function_name == "set_call_sentiment":
        sentiment = arguments.get("sentiment", "neutral")
        reason = arguments.get("reason", "")
        call_data["sentiment"] = sentiment
        call_data["sentiment_reason"] = reason
        logger.info(f"[{call_id[:8]}] 🎭 Sentiment: {sentiment} - {reason}")
        return json.dumps({"status": "success", "message": f"Duygu durumu kaydedildi: {sentiment}"})

    elif function_name == "add_call_tags":
        tags = arguments.get("tags", [])
        existing_tags = call_data.get("tags", [])
        call_data["tags"] = list(set(existing_tags + tags))
        logger.info(f"[{call_id[:8]}] 🏷️ Tags: {call_data['tags']}")
        return json.dumps({"status": "success", "message": f"Etiketler eklendi: {', '.join(tags)}"})

    elif function_name == "generate_call_summary":
        summary = arguments.get("summary", "")
        action_items = arguments.get("action_items", [])
        satisfaction = arguments.get("customer_satisfaction", "neutral")
        call_data["summary"] = summary
        call_data["action_items"] = action_items
        call_data["customer_satisfaction"] = satisfaction
        logger.info(f"[{call_id[:8]}] 📋 Summary: {summary[:100]}...")
        return json.dumps({"status": "success", "message": "Görüşme özeti kaydedildi"})

    elif function_name == "end_call":
        outcome = arguments.get("outcome", "success")
        summary = arguments.get("summary", "")
        call_data["outcome"] = outcome
        if summary:
            call_data["summary"] = summary
        call_data["end_call_requested"] = True
        logger.info(f"[{call_id[:8]}] 🔚 End call requested: outcome={outcome}")
        return json.dumps({"status": "success", "message": "Görüşme sonlandırılıyor. Müşteriye vedalaş."})

    return json.dumps({"status": "error", "message": f"Bilinmeyen fonksiyon: {function_name}"})


# ============================================================================
# ANA KÖPRÜ SINIFI
# ============================================================================

class CallBridge:
    """
    Tek bir çağrı için Asterisk AudioSocket ↔ OpenAI Realtime köprüsü.

    v4 - Native 24kHz:
    - Asterisk slin24 (0x13) → doğrudan base64 → OpenAI
    - OpenAI PCM16 24kHz → doğrudan 0x13 paket → Asterisk
    - Resampling yok, zero-copy passthrough
    """

    def __init__(self, call_uuid: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.call_uuid = call_uuid
        self.reader = reader
        self.writer = writer
        self.openai_ws: Optional[ClientConnection] = None
        self.is_active = True
        self.start_time = datetime.now()

        # Geçerli OpenAI Realtime ses seçenekleri
        self.VALID_VOICES = OPENAI_VALID_VOICES
        
        # Provider tracking (openai or xai)
        self.provider = "openai"  # Default, overridden from Redis call_setup
        
        # Agent ayarları (default değerler)
        self.agent_voice = "ash"
        self.agent_model = MODEL  # gpt-realtime-mini veya gpt-realtime
        self.agent_language = "tr"
        self.agent_prompt = SYSTEM_INSTRUCTIONS
        self.customer_name = None
        self.customer_title = None  # Mr/Mrs (translated at runtime by language)
        self.agent_name = "AI Agent"  # Agent display name for greeting
        self.customer_data = {}  # Customer data dict for greeting variable replacement
        self.greeting_message = None  # Agent's custom greeting message
        self.first_speaker = "agent"
        self.agent_temperature = 0.6
        # VAD settings - optimized for comprehension accuracy
        self.agent_vad_threshold = 0.5  # OpenAI recommended default (was 0.3 - too sensitive)
        self.agent_silence_duration_ms = 1000  # Give customer more time to finish (was 800)
        self.agent_prefix_padding_ms = 400  # Capture speech start (was 500, OpenAI recommends 300)
        self.agent_interrupt_response = True
        self.agent_create_response = True
        self.agent_noise_reduction = True
        self.agent_turn_detection = "semantic_vad"  # Semantic VAD for better turn detection (was server_vad)
        self.agent_vad_eagerness = "low"  # Don't interrupt customer prematurely
        # Transcription settings
        self.agent_transcript_model = "gpt-4o-transcribe"  # Best accuracy (was hardcoded gpt-4o-mini-transcribe)
        self.agent_max_output_tokens = 500  # Configurable from DB

        # SIP/Hangup tracking
        self.sip_code: Optional[int] = None  # SIP response code
        self.hangup_cause: Optional[str] = None  # Hangup reason text

        # Agent tracking
        self.agent_id: Optional[int] = None  # Agent DB ID for CallLog

        # Conversation phase tracking (for adaptive prompting)
        self.conversation_phase = "opening"  # opening, gathering, resolution, closing
        self.turn_count = 0  # Number of complete turns (user + agent)

        # Audio buffer - küçük chunk'ları biriktirip toplu gönderim
        # 100ms = 5x 20ms chunk → kesik ses sorununu önler
        self.audio_buffer = bytearray()
        self.buffer_target_ms = 100  # 60→100ms arttırıldı
        self.buffer_target_bytes = ASTERISK_SAMPLE_RATE * 2 * self.buffer_target_ms // 1000
        
        # Output buffer - OpenAI'den gelen sesi düzgün akıtmak için
        self.output_buffer = bytearray()
        self.output_buffer_min_ms = 40  # 40ms buffer dolmadan çalmaya başlama (80→40ms azaltıldı, daha hızlı ilk ses)

        # Asterisk'ten gelen audio tipi (otomatik algılama)
        self.detected_audio_type: Optional[int] = None

        # Function call state
        self.function_name = ""
        self.function_args = ""
        self.function_call_id = ""

        # İstatistikler
        self.stats = {
            "audio_frames_in": 0,
            "audio_frames_out": 0,
            "audio_bytes_in": 0,
            "audio_bytes_out": 0,
            "tool_calls": 0,
            "errors": 0,
        }

    async def start(self):
        """Köprüyü başlat."""
        logger.info(f"[{self.call_uuid[:8]}] 📞 Çağrı başlatılıyor...")

        # ================================================================
        # 1) Önce Redis'ten agent ayarlarını al (outbound çağrılar)
        # ================================================================
        call_setup = await get_call_setup_from_redis(self.call_uuid)
        
        if call_setup:
            # Redis'te bulundu - outbound çağrı, agent ayarları mevcut
            # Detect provider (openai or xai)
            self.provider = call_setup.get("provider") or "openai"
            
            if self.provider == "xai":
                # xAI Grok voices
                self.VALID_VOICES = XAI_VALID_VOICES
                voice = call_setup.get("voice") or "Ara"
                self.agent_voice = voice if voice in self.VALID_VOICES else "Ara"
                self.agent_model = call_setup.get("model") or "grok-2-realtime"
            elif self.provider == "gemini":
                # Google Gemini voices
                self.VALID_VOICES = GEMINI_VALID_VOICES
                voice = call_setup.get("voice") or "Kore"
                self.agent_voice = voice if voice in self.VALID_VOICES else "Kore"
                self.agent_model = call_setup.get("model") or GEMINI_DEFAULT_MODEL
            else:
                voice = call_setup.get("voice") or "ash"
                self.agent_voice = voice if voice in self.VALID_VOICES else "ash"
                self.agent_model = call_setup.get("model") or MODEL
            self.agent_language = call_setup.get("language") or "tr"
            self.agent_prompt = call_setup.get("prompt") or SYSTEM_INSTRUCTIONS
            self.customer_name = call_setup.get("customer_name") or None
            self.customer_title = call_setup.get("customer_title") or None
            self.agent_name = call_setup.get("agent_name") or "AI Agent"
            self.customer_data = call_setup.get("customer_data") or {}
            # Store agent_id for CallLog tracking
            agent_id_val = call_setup.get("agent_id")
            self.agent_id = int(agent_id_val) if agent_id_val else None
            self.greeting_message = call_setup.get("greeting_message") or None
            self.first_speaker = call_setup.get("first_speaker") or "agent"
            self.agent_temperature = float(call_setup.get("temperature", 0.6))
            # VAD and interrupt settings
            self.agent_vad_threshold = float(call_setup.get("vad_threshold", 0.5))
            self.agent_silence_duration_ms = int(call_setup.get("silence_duration_ms", 1000))
            self.agent_prefix_padding_ms = int(call_setup.get("prefix_padding_ms", 400))
            self.agent_interrupt_response = call_setup.get("interrupt_response", True)
            self.agent_create_response = call_setup.get("create_response", True)
            self.agent_noise_reduction = call_setup.get("noise_reduction", True)
            self.agent_turn_detection = call_setup.get("turn_detection", "semantic_vad")
            self.agent_vad_eagerness = call_setup.get("vad_eagerness", "low")
            # Transcription & output settings from DB
            self.agent_transcript_model = call_setup.get("transcript_model", "gpt-4o-transcribe")
            self.agent_max_output_tokens = int(call_setup.get("max_output_tokens", 500))
            
            # Note: conversation_history is already included by PromptBuilder
            logger.info(f"[{self.call_uuid[:8]}] Agent '{call_setup.get('agent_name', 'Unknown')}' loaded from Redis: "
                        f"voice={self.agent_voice}, model={self.agent_model}, lang={self.agent_language}, vad={self.agent_vad_threshold}")
        else:
            # ================================================================
            # 2) Redis'te yoksa ARI + DB fallback (inbound çağrılar)
            # ================================================================
            channel_vars = await get_channel_variables(self.call_uuid)
            
            agent_id_str = channel_vars.get("VOICEAI_AGENT_ID")
            if agent_id_str:
                try:
                    agent_id = int(agent_id_str)
                    self.agent_id = agent_id
                    agent_data = await get_agent_from_db(agent_id)
                    
                    if agent_data:
                        voice = agent_data["voice"] or "ash"
                        self.agent_voice = voice if voice in self.VALID_VOICES else "ash"
                        if voice != self.agent_voice:
                            logger.warning(f"[{self.call_uuid[:8]}] Invalid voice '{voice}', using 'ash'")
                        self.agent_model = agent_data["model_type"]
                        self.agent_language = agent_data["language"]
                        # Build complete prompt using PromptBuilder
                        from app.services.prompt_builder import PromptBuilder, PromptContext
                        ctx = PromptContext.from_dict(
                            agent_data,
                            customer_name=self.customer_name or "",
                        )
                        self.agent_prompt = PromptBuilder.build(ctx) or SYSTEM_INSTRUCTIONS
                        self.greeting_message = agent_data.get("greeting_message") or self.greeting_message
                        self.first_speaker = agent_data.get("first_speaker") or self.first_speaker
                        # Comprehension-critical settings from DB
                        self.agent_transcript_model = agent_data.get("transcript_model", "gpt-4o-transcribe")
                        self.agent_temperature = float(agent_data.get("temperature", 0.6))
                        self.agent_vad_threshold = float(agent_data.get("vad_threshold", 0.5))
                        self.agent_silence_duration_ms = int(agent_data.get("silence_duration_ms", 1000))
                        self.agent_prefix_padding_ms = int(agent_data.get("prefix_padding_ms", 400))
                        self.agent_turn_detection = agent_data.get("turn_detection", "semantic_vad")
                        self.agent_vad_eagerness = agent_data.get("vad_eagerness", "low")
                        self.agent_max_output_tokens = int(agent_data.get("max_output_tokens", 500))
                        self.agent_noise_reduction = agent_data.get("noise_reduction", True)
                        self.agent_interrupt_response = agent_data.get("interrupt_response", True)
                        self.agent_create_response = agent_data.get("create_response", True)
                        
                        logger.info(f"[{self.call_uuid[:8]}] ✅ Agent '{agent_data['name']}' yüklendi (ARI fallback): "
                                    f"voice={self.agent_voice}, model={self.agent_model}, lang={self.agent_language}, "
                                    f"vad={self.agent_turn_detection}, transcript={self.agent_transcript_model}")
                    else:
                        logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Agent ID {agent_id} database'de bulunamadı, default ayarlar kullanılıyor")
                except Exception as e:
                    logger.error(f"[{self.call_uuid[:8]}] ❌ Agent bilgileri alınamadı: {e}")
            
            # Customer name and title from ARI
            self.customer_name = channel_vars.get("VOICEAI_CUSTOMER_NAME")
            self.customer_title = channel_vars.get("VOICEAI_CUSTOMER_TITLE") or self.customer_title
        
        if self.customer_name:
            logger.info(f"[{self.call_uuid[:8]}] 👤 Müşteri ismi: {self.customer_name}")

        active_calls[self.call_uuid] = {
            "customer": {},
            "start_time": self.start_time.isoformat(),
            "transfer_requested": False,
        }

        try:
            # TCP_NODELAY: Disable Nagle's algorithm for lower audio latency
            sock = self.writer.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                logger.debug(f"[{self.call_uuid[:8]}] 🔧 TCP_NODELAY enabled")

            t_connect_start = time.monotonic()
            await self._connect_openai()
            t_connected = time.monotonic()
            logger.info(f"[{self.call_uuid[:8]}] ⏱️ WebSocket connect: {(t_connected - t_connect_start)*1000:.0f}ms")
            
            # Configure session immediately after connect — don't wait for
            # session.created (OpenAI) or conversation.created (xAI).
            # These are informational events; the session is ready as soon as
            # the WebSocket handshake completes.  Skipping the wait saves
            # ~500-1000ms of round-trip latency.
            # Gemini: setup is already done inside _connect_gemini.
            if self.provider == "gemini":
                pass  # _connect_gemini already handles setup + setupComplete
            else:
                await self._configure_session()
                # Wait only for session.updated to confirm settings applied.
                # session.created / conversation.created will be consumed and skipped.
                await self._wait_for_event("session.updated", timeout=3.0)
            
            t_configured = time.monotonic()
            logger.info(f"[{self.call_uuid[:8]}] ⏱️ Session config: {(t_configured - t_connected)*1000:.0f}ms")

            await self._trigger_greeting()
            t_greeting = time.monotonic()
            logger.info(f"[{self.call_uuid[:8]}] ⏱️ Total setup: {(t_greeting - t_connect_start)*1000:.0f}ms "
                         f"(connect={((t_connected - t_connect_start)*1000):.0f} + "
                         f"config={((t_configured - t_connected)*1000):.0f} + "
                         f"greeting={((t_greeting - t_configured)*1000):.0f})")

            if self.provider == "gemini":
                await asyncio.gather(
                    self._asterisk_to_gemini(),
                    self._gemini_to_asterisk(),
                    self._check_hangup_signal(),
                )
            else:
                await asyncio.gather(
                    self._asterisk_to_openai(),
                    self._openai_to_asterisk(),
                    self._check_hangup_signal(),
                )
        except Exception as e:
            logger.error(f"[{self.call_uuid[:8]}] Bridge error: {e}")
            self.stats["errors"] += 1
            if not self.sip_code:
                self.sip_code = 500
                self.hangup_cause = "Internal bridge error"
        finally:
            await self._cleanup()

    async def _connect_openai(self):
        """Connect to OpenAI, xAI, or Gemini Realtime WebSocket based on provider."""
        if self.provider == "gemini":
            await self._connect_gemini()
            return
        
        if self.provider == "xai":
            # xAI Grok: model is sent in session config, not URL
            ws_url = XAI_WS_URL
            api_key = XAI_API_KEY
            headers = {
                "Authorization": f"Bearer {api_key}",
            }
            provider_label = "xAI Grok"
        else:
            # OpenAI Realtime: model in URL, requires OpenAI-Beta header
            ws_url = f"wss://api.openai.com/v1/realtime?model={self.agent_model}"
            api_key = OPENAI_API_KEY
            headers = {
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1",
            }
            provider_label = "OpenAI"
        
        self.openai_ws = await ws_connect(
            ws_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
            max_size=10 * 1024 * 1024,
        )
        logger.info(f"[{self.call_uuid[:8]}] 🔌 {provider_label} bağlantısı kuruldu (model: {self.agent_model})")

    async def _connect_gemini(self):
        """
        Connect to Google Gemini Live API via Vertex AI WebSocket.
        Sends setup message and waits for setupComplete.
        
        Gemini uses a completely different protocol than OpenAI/xAI:
        - OAuth2 Bearer auth (from service account)
        - Setup message as first frame (contains model, voice, system instruction, tools)
        - setupComplete event confirms ready state
        """
        # Get OAuth2 access token
        access_token = _get_gemini_access_token()
        
        # Build WebSocket URL
        location = GOOGLE_LOCATION or "us-central1"
        ws_url = GEMINI_WS_URL_TEMPLATE.format(location=location)
        
        # Build model resource name for Vertex AI
        project_id = GOOGLE_PROJECT_ID
        if not project_id:
            raise ValueError("GOOGLE_PROJECT_ID is required for Gemini provider")
        
        model_resource = (
            f"projects/{project_id}/locations/{location}"
            f"/publishers/google/models/{self.agent_model}"
        )
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        self.openai_ws = await ws_connect(
            ws_url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
            max_size=10 * 1024 * 1024,
        )
        logger.info(f"[{self.call_uuid[:8]}] 🔌 Gemini bağlantısı kuruldu (model: {self.agent_model})")
        
        # Build and send setup message (must be first message)
        instructions = self.agent_prompt or "You are a helpful voice assistant."
        
        setup_msg = {
            "setup": {
                "model": model_resource,
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": self.agent_voice
                            }
                        }
                    },
                    "temperature": self.agent_temperature,
                },
                "systemInstruction": {
                    "parts": [{"text": instructions}]
                },
                "tools": _build_gemini_tools(),
            }
        }
        
        await self.openai_ws.send(json.dumps(setup_msg))
        logger.info(f"[{self.call_uuid[:8]}] ⚙️ Gemini setup gönderildi: voice={self.agent_voice}, model={self.agent_model}")
        
        # Wait for setupComplete
        try:
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                msg = await asyncio.wait_for(self.openai_ws.recv(), timeout=remaining)
                event = json.loads(msg)
                if "setupComplete" in event:
                    logger.info(f"[{self.call_uuid[:8]}] ✅ Gemini setupComplete alındı")
                    return
                logger.debug(f"[{self.call_uuid[:8]}] ⏳ Gemini beklenen: setupComplete, gelen: {list(event.keys())}")
        except asyncio.TimeoutError:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Gemini setupComplete için timeout, devam ediliyor")

    async def _wait_for_event(self, target_type: str, timeout: float = 5.0):
        """
        Wait for a specific OpenAI event by type.
        Replaces arbitrary asyncio.sleep() with deterministic event waiting.
        Consumed events (session.created, session.updated) are not needed by _openai_to_asterisk.
        """
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                msg = await asyncio.wait_for(self.openai_ws.recv(), timeout=remaining)
                event = json.loads(msg)
                etype = event.get("type", "")
                if etype == target_type:
                    logger.info(f"[{self.call_uuid[:8]}] ✅ {target_type} alındı")
                    return event
                logger.debug(f"[{self.call_uuid[:8]}] ⏳ Beklenen: {target_type}, gelen: {etype}")
        except asyncio.TimeoutError:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ {target_type} için {timeout}s timeout, devam ediliyor")
        except Exception as e:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ {target_type} beklenirken hata: {e}")
        return None

    def _get_localized_title(self) -> str:
        """Translate Mr/Mrs to the agent's language."""
        if not self.customer_title:
            return ""
        lang = self.agent_language or "en"
        translations = TITLE_TRANSLATIONS.get(lang, TITLE_TRANSLATIONS["en"])
        return translations.get(self.customer_title, self.customer_title)

    def _get_addressed_name(self) -> str:
        """Get full addressed name with title in correct order for the language.
        Turkish: 'Cenani Bey', English: 'Mr Cenani', German: 'Herr Cenani'
        """
        if not self.customer_name:
            return ""
        title = self._get_localized_title()
        if not title:
            return self.customer_name
        lang = self.agent_language or "en"
        if lang in TITLE_AFTER_NAME:
            return f"{self.customer_name} {title}"
        else:
            return f"{title} {self.customer_name}"

    async def _configure_session(self):
        """Configure OpenAI session with agent settings.

        Note: Customer context, voice rules, AMD backup, and safety sections
        are already included by PromptBuilder (via openai_provider.py or
        get_agent_from_db fallback). No inline injection needed.
        """
        instructions = self.agent_prompt

        # Build turn_detection config based on VAD type
        if self.agent_turn_detection == "semantic_vad":
            # Semantic VAD: Uses semantic understanding to detect end of speech
            # Much better for gpt-realtime-mini - understands when customer finished speaking
            turn_detection_config = {
                "type": "semantic_vad",
                "eagerness": self.agent_vad_eagerness,  # low/medium/high/auto
                "create_response": self.agent_create_response,
                "interrupt_response": self.agent_interrupt_response,
            }
        else:
            # Server VAD: Simple silence-based detection (fallback)
            turn_detection_config = {
                "type": "server_vad",
                "threshold": self.agent_vad_threshold,
                "prefix_padding_ms": self.agent_prefix_padding_ms,
                "silence_duration_ms": self.agent_silence_duration_ms,
                "create_response": self.agent_create_response,
                "interrupt_response": self.agent_interrupt_response,
            }
        
        # Build session config — xAI and OpenAI use different schemas
        if self.provider == "xai":
            # xAI Grok session config
            # Docs: https://docs.x.ai/developers/model-capabilities/audio/voice-agent
            xai_turn_detection = {"type": "server_vad"}
            if self.agent_turn_detection == "server_vad":
                xai_turn_detection = {"type": "server_vad"}
            
            config = {
                "type": "session.update",
                "session": {
                    "model": self.agent_model,  # xAI requires model in session
                    "voice": self.agent_voice,
                    "instructions": instructions,
                    "turn_detection": xai_turn_detection,
                    "audio": {
                        "input": {"format": {"type": "audio/pcm", "rate": 24000}},
                        "output": {"format": {"type": "audio/pcm", "rate": 24000}},
                    },
                    "tools": _build_tools(),
                }
            }
        else:
            # OpenAI Realtime session config
            config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "voice": self.agent_voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "instructions": instructions,
                    "temperature": self.agent_temperature,
                    "turn_detection": turn_detection_config,
                    "input_audio_transcription": {
                        "model": self.agent_transcript_model,
                        "language": self.agent_language,
                    },
                    "tools": _build_tools(),
                    "tool_choice": "auto",
                    "max_response_output_tokens": self.agent_max_output_tokens,
                }
            }
        
            # Noise reduction: only include when enabled (OpenAI only)
            if self.agent_noise_reduction:
                config["session"]["input_audio_noise_reduction"] = {"type": "near_field"}
                logger.info(f"[{self.call_uuid[:8]}] 🔇 Noise reduction aktif: near_field")
        
        await self.openai_ws.send(json.dumps(config))
        logger.info(f"[{self.call_uuid[:8]}] ⚙️ Session yapılandırıldı: voice={self.agent_voice}, lang={self.agent_language}, "
                     f"temp={self.agent_temperature}, vad={self.agent_turn_detection}, transcript={self.agent_transcript_model}, "
                     f"noise_reduction={self.agent_noise_reduction}")

    async def _trigger_greeting(self):
        """Trigger initial greeting based on agent settings."""
        # If first_speaker = 'user', skip greeting and wait for customer to speak
        if self.first_speaker == "user":
            logger.info(f"[{self.call_uuid[:8]}] first_speaker=user, skipping greeting - waiting for customer")
            return

        # Use agent's custom greeting message if available
        if self.greeting_message:
            # Build customer_data dict for process_greeting
            from app.services.greeting_processor import process_greeting
            greeting_customer_data = {
                "name": self.customer_name or "",
                "customer_title": self.customer_title or "",  # Raw "Mr"/"Mrs"
                "custom_data": self.customer_data,
            }

            greeting = process_greeting(
                template=self.greeting_message,
                customer_data=greeting_customer_data,
                agent_name=self.agent_name,
                language=self.agent_language or "tr",
            )
            
            greeting_instruction = f"Greet the customer by saying EXACTLY this text: '{greeting}'"
        else:
            # Default greeting
            greeting_instruction = "Greet the customer with a brief welcome message."
        
        # Build response.create payload
        response_payload = {
            "instructions": greeting_instruction
        }
        # xAI requires modalities in response.create
        if self.provider == "xai":
            response_payload["modalities"] = ["text", "audio"]
        
        if self.provider == "gemini":
            # Gemini uses clientContent to send text instruction for greeting
            await self.openai_ws.send(json.dumps({
                "clientContent": {
                    "turns": [{
                        "role": "user",
                        "parts": [{"text": greeting_instruction}]
                    }],
                    "turnComplete": True
                }
            }))
        else:
            await self.openai_ws.send(json.dumps({
                "type": "response.create",
                "response": response_payload
            }))
        logger.info(f"[{self.call_uuid[:8]}] 🎙️ Greeting gönderildi: {greeting_instruction[:80]}...")

    # ---- Asterisk → OpenAI ----

    async def _asterisk_to_openai(self):
        """
        Asterisk'ten 24kHz PCM16 al, doğrudan OpenAI'ye gönder.
        *** RESAMPLING YOK - zero-copy audio passthrough ***
        """
        try:
            while self.is_active:
                msg_type, payload = await read_audiosocket_message(self.reader)

                if msg_type == MSG_HANGUP:
                    logger.info(f"[{self.call_uuid[:8]}] 📴 Asterisk hangup")
                    self.sip_code = self.sip_code or 200
                    self.hangup_cause = self.hangup_cause or "Normal Clearing"
                    self.is_active = False
                    break

                elif msg_type == MSG_UUID:
                    pass

                elif msg_type == MSG_DTMF:
                    dtmf_digit = payload.decode("ascii", errors="ignore") if payload else ""
                    if dtmf_digit:
                        logger.info(f"[{self.call_uuid[:8]}] 🔢 DTMF: {dtmf_digit}")
                        await self._send_dtmf_as_text(dtmf_digit)

                elif msg_type in AUDIO_MSG_TYPES:
                    # İlk frame'de formatı logla
                    if self.detected_audio_type is None:
                        self.detected_audio_type = msg_type
                        rate_map = {0x10: "8kHz", 0x12: "16kHz", 0x13: "24kHz", 0x16: "48kHz"}
                        detected = rate_map.get(msg_type, f"0x{msg_type:02x}")
                        logger.info(
                            f"[{self.call_uuid[:8]}] 🎵 Audio: {detected} (chunk={len(payload)}B)"
                        )

                        if msg_type != MSG_AUDIO_24K:
                            logger.warning(
                                f"[{self.call_uuid[:8]}] ⚠️ Beklenen 24kHz (0x13), gelen {detected}! "
                                f"Dial(AudioSocket/.../c(slin24)) kullanın"
                            )

                    self.stats["audio_frames_in"] += 1
                    self.stats["audio_bytes_in"] += len(payload)

                    # Buffer'a ekle
                    self.audio_buffer.extend(payload)

                    # 60ms dolduğunda toplu gönder
                    if len(self.audio_buffer) >= self.buffer_target_bytes:
                        audio_pcm = bytes(self.audio_buffer)
                        self.audio_buffer.clear()

                        # Save input (customer) audio to Redis for recording
                        asyncio.create_task(save_audio_to_redis(self.call_uuid, audio_pcm, "input"))

                        b64_audio = base64.b64encode(audio_pcm).decode("utf-8")

                        if self.openai_ws and self.openai_ws.state == State.OPEN:
                            await self.openai_ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": b64_audio,
                            }))

                elif msg_type == MSG_ERROR:
                    error_code = payload[0] if payload else 0xFF
                    logger.error(f"[{self.call_uuid[:8]}] ❌ AudioSocket error: 0x{error_code:02x}")
                    self.stats["errors"] += 1

        except asyncio.IncompleteReadError:
            logger.info(f"[{self.call_uuid[:8]}] 📴 Asterisk bağlantısı kapandı")
        except Exception as e:
            logger.error(f"[{self.call_uuid[:8]}] ❌ Asterisk okuma hatası: {e}")
        finally:
            self.is_active = False

    async def _send_dtmf_as_text(self, digit: str):
        """DTMF tuşunu metin olarak OpenAI'ye gönder."""
        if self.openai_ws and self.openai_ws.state == State.OPEN:
            await self.openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": f"[Müşteri {digit} tuşuna bastı]"}]
                }
            }))

    # ---- OpenAI → Asterisk ----

    async def _openai_to_asterisk(self):
        """
        OpenAI'den gelen 24kHz PCM16'yı buffer'layarak Asterisk'e gönder.
        Kesik ses sorununu önlemek için output buffering eklendi.
        """
        try:
            pacer_interval = CHUNK_DURATION_MS / 1000.0
            next_send_time: Optional[float] = None
            output_buffer_min_bytes = ASTERISK_SAMPLE_RATE * 2 * self.output_buffer_min_ms // 1000
            is_playing = False
            
            async for message in self.openai_ws:
                if not self.is_active:
                    break

                event = json.loads(message)
                event_type = event.get("type", "")

                # Publish event to Redis for SSE streaming (filtered events only)
                publishable_events = [
                    "session.created", "session.updated", "conversation.created",
                    "input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped",
                    "conversation.item.input_audio_transcription.completed",
                    "response.created",
                    "response.audio_transcript.delta", "response.audio_transcript.done",
                    "response.output_audio_transcript.delta", "response.output_audio_transcript.done",
                    "response.done", "rate_limits.updated", "error"
                ]
                if event_type in publishable_events:
                    # Don't await - fire and forget to avoid blocking
                    asyncio.create_task(publish_event_to_redis(self.call_uuid, event))

                if event_type in ("session.created", "conversation.created"):
                    logger.info(f"[{self.call_uuid[:8]}] 🎙️ Realtime session hazır ({event_type})")

                elif event_type == "input_audio_buffer.speech_started":
                    # User started speaking - interrupt AI response
                    if self.agent_interrupt_response:
                        logger.debug(f"[{self.call_uuid[:8]}] 👂 Müşteri konuşuyor - AI yanıtı durduruluyor")
                        # Clear output buffer to stop AI audio immediately
                        self.output_buffer.clear()
                        is_playing = False
                        next_send_time = None
                        # Send response.cancel to stop AI
                        await self.openai_ws.send(json.dumps({"type": "response.cancel"}))

                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.debug(f"[{self.call_uuid[:8]}] 👂 Müşteri konuşmayı bitirdi")

                elif event_type in ("response.audio.delta", "response.output_audio.delta"):
                    audio_b64 = event.get("delta", "")
                    if audio_b64:
                        audio_pcm_24k = base64.b64decode(audio_b64)
                        self.output_buffer.extend(audio_pcm_24k)
                        
                        # Save audio to Redis for recording download
                        asyncio.create_task(save_audio_to_redis(self.call_uuid, audio_pcm_24k, "output"))
                        
                        # Buffer dolana kadar bekle, sonra akışa başla
                        if not is_playing and len(self.output_buffer) < output_buffer_min_bytes:
                            continue
                        
                        is_playing = True
                        
                        # Buffer'dan chunk'ları gönder
                        while len(self.output_buffer) >= ASTERISK_CHUNK_BYTES:
                            chunk = bytes(self.output_buffer[:ASTERISK_CHUNK_BYTES])
                            del self.output_buffer[:ASTERISK_CHUNK_BYTES]

                            if next_send_time is None:
                                next_send_time = time.monotonic()
                            else:
                                next_send_time += pacer_interval

                            delay = next_send_time - time.monotonic()
                            if delay > 0:
                                await asyncio.sleep(delay)

                            msg = build_audiosocket_message(MSG_AUDIO_24K, chunk)
                            self.writer.write(msg)
                            self.stats["audio_frames_out"] += 1
                            self.stats["audio_bytes_out"] += len(chunk)

                        await self.writer.drain()
                
                elif event_type in ("response.audio.done", "response.output_audio.done"):
                    # Yanıt bitti, kalan buffer'ı temizle
                    while len(self.output_buffer) >= ASTERISK_CHUNK_BYTES:
                        chunk = bytes(self.output_buffer[:ASTERISK_CHUNK_BYTES])
                        del self.output_buffer[:ASTERISK_CHUNK_BYTES]
                        msg = build_audiosocket_message(MSG_AUDIO_24K, chunk)
                        self.writer.write(msg)
                        if next_send_time:
                            next_send_time += pacer_interval
                            delay = next_send_time - time.monotonic()
                            if delay > 0:
                                await asyncio.sleep(delay)
                    
                    # Kalan kısa chunk'ı padding ile gönder
                    if len(self.output_buffer) > 0:
                        chunk = bytes(self.output_buffer) + b'\x00' * (ASTERISK_CHUNK_BYTES - len(self.output_buffer))
                        self.output_buffer.clear()
                        msg = build_audiosocket_message(MSG_AUDIO_24K, chunk)
                        self.writer.write(msg)
                    
                    await self.writer.drain()
                    is_playing = False
                    next_send_time = None

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    if transcript:
                        logger.info(f"[{self.call_uuid[:8]}] 🗣️ Müşteri: \"{transcript}\"")
                        # Save to Redis for real-time transcript
                        await save_transcript_to_redis(self.call_uuid, "user", transcript)
                        # Track turns for adaptive prompting
                        self.turn_count += 1
                        await self._update_conversation_phase(transcript)

                elif event_type in ("response.audio_transcript.done", "response.output_audio_transcript.done"):
                    transcript = event.get("transcript", "")
                    if transcript:
                        logger.info(f"[{self.call_uuid[:8]}] 🤖 Agent: \"{transcript}\"")
                        # Save to Redis for real-time transcript
                        await save_transcript_to_redis(self.call_uuid, "assistant", transcript)

                elif event_type == "response.output_item.added":
                    item = event.get("item", {})
                    if item.get("type") == "function_call":
                        self.function_name = item.get("name", "")
                        self.function_call_id = item.get("call_id", "")
                        self.function_args = ""

                elif event_type == "response.function_call_arguments.delta":
                    self.function_args += event.get("delta", "")

                elif event_type == "response.output_item.done":
                    item = event.get("item", {})
                    if item.get("type") == "function_call":
                        await self._process_tool_call(item)

                elif event_type == "response.done":
                    usage = event.get("response", {}).get("usage", {})
                    if usage:
                        logger.debug(
                            f"[{self.call_uuid[:8]}] 📊 Tokens: "
                            f"in={usage.get('input_tokens', 0)} out={usage.get('output_tokens', 0)}"
                        )
                        # Save usage to Redis for cost tracking
                        asyncio.create_task(save_usage_to_redis(self.call_uuid, usage, MODEL))

                elif event_type == "error":
                    error = event.get("error", {})
                    logger.error(f"[{self.call_uuid[:8]}] ❌ OpenAI: {error.get('message', '')}")
                    self.stats["errors"] += 1

                elif event_type == "rate_limits.updated":
                    for limit in event.get("rate_limits", []):
                        if limit.get("remaining", 999) < 5:
                            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Rate limit: {limit}")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"[{self.call_uuid[:8]}] 🔌 OpenAI kapandı: {e}")
        except Exception as e:
            logger.error(f"[{self.call_uuid[:8]}] ❌ OpenAI event hatası: {e}")
        finally:
            self.is_active = False

    # ---- Asterisk → Gemini (Google) ----

    async def _asterisk_to_gemini(self):
        """
        Read 24kHz PCM16 from Asterisk and send to Gemini Live API.
        Gemini uses realtimeInput.audio format with mime type.
        """
        try:
            while self.is_active:
                msg_type, payload = await read_audiosocket_message(self.reader)

                if msg_type == MSG_HANGUP:
                    logger.info(f"[{self.call_uuid[:8]}] 📴 Asterisk hangup")
                    self.sip_code = self.sip_code or 200
                    self.hangup_cause = self.hangup_cause or "Normal Clearing"
                    self.is_active = False
                    break

                elif msg_type == MSG_UUID:
                    pass

                elif msg_type == MSG_DTMF:
                    digit = payload.decode("ascii", errors="replace").strip()
                    logger.info(f"[{self.call_uuid[:8]}] 📱 DTMF: {digit}")

                elif msg_type in (MSG_AUDIO_8K, MSG_AUDIO_16K, MSG_AUDIO_24K, MSG_AUDIO_48K):
                    self.stats["audio_frames_in"] += 1
                    self.stats["audio_bytes_in"] += len(payload)

                    # Buffer audio
                    self.audio_buffer.extend(payload)

                    # Send when buffer is full (60ms chunks)
                    if len(self.audio_buffer) >= self.buffer_target_bytes:
                        audio_pcm = bytes(self.audio_buffer)
                        self.audio_buffer.clear()

                        # Save input audio to Redis for recording
                        asyncio.create_task(save_audio_to_redis(self.call_uuid, audio_pcm, "input"))

                        b64_audio = base64.b64encode(audio_pcm).decode("utf-8")

                        if self.openai_ws and self.openai_ws.state == State.OPEN:
                            # Gemini format: realtimeInput with mime type
                            await self.openai_ws.send(json.dumps({
                                "realtimeInput": {
                                    "audio": {
                                        "data": b64_audio,
                                        "mimeType": "audio/pcm;rate=24000"
                                    }
                                }
                            }))

                elif msg_type == MSG_ERROR:
                    error_code = payload[0] if payload else 0xFF
                    logger.error(f"[{self.call_uuid[:8]}] ❌ AudioSocket error: 0x{error_code:02x}")
                    self.stats["errors"] += 1

        except asyncio.IncompleteReadError:
            logger.info(f"[{self.call_uuid[:8]}] 📴 Asterisk bağlantısı kapandı")
        except Exception as e:
            logger.error(f"[{self.call_uuid[:8]}] ❌ Asterisk okuma hatası (Gemini): {e}")
        finally:
            self.is_active = False

    # ---- Gemini → Asterisk ----

    async def _gemini_to_asterisk(self):
        """
        Handle Gemini Live API server messages and send audio to Asterisk.
        Gemini uses a completely different event format than OpenAI/xAI:
        - serverContent.modelTurn.parts[].inlineData.data for audio
        - toolCall.functionCalls[] for tool invocations
        - serverContent.turnComplete for end of response
        - serverContent.interrupted for user interruption
        """
        try:
            pacer_interval = CHUNK_DURATION_MS / 1000.0
            next_send_time: Optional[float] = None
            output_buffer_min_bytes = ASTERISK_SAMPLE_RATE * 2 * self.output_buffer_min_ms // 1000
            is_playing = False
            
            async for message in self.openai_ws:
                if not self.is_active:
                    break

                event = json.loads(message)

                # ── Audio output from model ──
                server_content = event.get("serverContent")
                if server_content:
                    model_turn = server_content.get("modelTurn")
                    if model_turn:
                        parts = model_turn.get("parts", [])
                        for part in parts:
                            inline_data = part.get("inlineData")
                            if inline_data:
                                audio_b64 = inline_data.get("data", "")
                                mime_type = inline_data.get("mimeType", "")
                                
                                if audio_b64:
                                    audio_pcm = base64.b64decode(audio_b64)
                                    self.output_buffer.extend(audio_pcm)
                                    
                                    # Save audio to Redis for recording
                                    asyncio.create_task(save_audio_to_redis(self.call_uuid, audio_pcm, "output"))
                                    
                                    # Buffer until minimum, then stream
                                    if not is_playing and len(self.output_buffer) < output_buffer_min_bytes:
                                        continue
                                    
                                    is_playing = True
                                    
                                    # Send chunks to Asterisk
                                    while len(self.output_buffer) >= ASTERISK_CHUNK_BYTES:
                                        chunk = bytes(self.output_buffer[:ASTERISK_CHUNK_BYTES])
                                        del self.output_buffer[:ASTERISK_CHUNK_BYTES]

                                        if next_send_time is None:
                                            next_send_time = time.monotonic()
                                        else:
                                            next_send_time += pacer_interval

                                        delay = next_send_time - time.monotonic()
                                        if delay > 0:
                                            await asyncio.sleep(delay)

                                        msg = build_audiosocket_message(MSG_AUDIO_24K, chunk)
                                        self.writer.write(msg)
                                        self.stats["audio_frames_out"] += 1
                                        self.stats["audio_bytes_out"] += len(chunk)

                                    await self.writer.drain()
                            
                            # Text part (transcript)
                            text = part.get("text")
                            if text:
                                logger.info(f"[{self.call_uuid[:8]}] 🤖 Agent: \"{text}\"")
                                await save_transcript_to_redis(self.call_uuid, "assistant", text)
                    
                    # Turn complete - flush remaining buffer
                    if server_content.get("turnComplete"):
                        while len(self.output_buffer) >= ASTERISK_CHUNK_BYTES:
                            chunk = bytes(self.output_buffer[:ASTERISK_CHUNK_BYTES])
                            del self.output_buffer[:ASTERISK_CHUNK_BYTES]
                            msg = build_audiosocket_message(MSG_AUDIO_24K, chunk)
                            self.writer.write(msg)
                            if next_send_time:
                                next_send_time += pacer_interval
                                delay = next_send_time - time.monotonic()
                                if delay > 0:
                                    await asyncio.sleep(delay)
                        
                        # Flush remaining short chunk with padding
                        if len(self.output_buffer) > 0:
                            chunk = bytes(self.output_buffer) + b'\x00' * (ASTERISK_CHUNK_BYTES - len(self.output_buffer))
                            self.output_buffer.clear()
                            msg = build_audiosocket_message(MSG_AUDIO_24K, chunk)
                            self.writer.write(msg)
                        
                        await self.writer.drain()
                        is_playing = False
                        next_send_time = None
                        logger.debug(f"[{self.call_uuid[:8]}] ✅ Gemini turn complete")
                    
                    # User interruption
                    if server_content.get("interrupted"):
                        logger.debug(f"[{self.call_uuid[:8]}] 👂 Gemini interrupted - clearing buffer")
                        self.output_buffer.clear()
                        is_playing = False
                        next_send_time = None
                    
                    # Input transcription from Gemini
                    input_transcription = server_content.get("inputTranscription")
                    if input_transcription:
                        text = input_transcription.get("text", "")
                        if text:
                            logger.info(f"[{self.call_uuid[:8]}] 🗣️ Müşteri: \"{text}\"")
                            await save_transcript_to_redis(self.call_uuid, "user", text)
                            self.turn_count += 1

                # ── Tool calls ──
                tool_call = event.get("toolCall")
                if tool_call:
                    function_calls = tool_call.get("functionCalls", [])
                    for fc in function_calls:
                        await self._process_gemini_tool_call(fc)

                # ── Usage/metadata ──
                usage_metadata = event.get("usageMetadata")
                if usage_metadata:
                    logger.debug(
                        f"[{self.call_uuid[:8]}] 📊 Gemini tokens: "
                        f"prompt={usage_metadata.get('promptTokenCount', 0)} "
                        f"response={usage_metadata.get('responseTokenCount', 0)}"
                    )

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"[{self.call_uuid[:8]}] 🔌 Gemini kapandı: {e}")
        except Exception as e:
            logger.error(f"[{self.call_uuid[:8]}] ❌ Gemini event hatası: {e}")
        finally:
            self.is_active = False

    async def _process_gemini_tool_call(self, fc: dict):
        """Process a Gemini tool call and send response back."""
        func_name = fc.get("name", "")
        call_id = fc.get("id", "")
        args = fc.get("args", {})

        logger.info(f"[{self.call_uuid[:8]}] 🔧 Gemini Tool: {func_name}({json.dumps(args, ensure_ascii=False)})")
        self.stats["tool_calls"] += 1

        result = handle_tool_call(self.call_uuid, func_name, args)

        # Send tool response in Gemini format
        await self.openai_ws.send(json.dumps({
            "toolResponse": {
                "functionResponses": [{
                    "response": {"result": result},
                    "id": call_id
                }]
            }
        }))

        call_data = active_calls.get(self.call_uuid, {})
        if call_data.get("transfer_requested"):
            logger.info(f"[{self.call_uuid[:8]}] 🔄 Transfer istendi")

        # Agent requested call end → delayed hangup
        if call_data.get("end_call_requested"):
            logger.info(f"[{self.call_uuid[:8]}] 🔚 End call → delayed hangup (3s)")
            asyncio.create_task(self._delayed_hangup(3))

    async def _process_tool_call(self, item: dict):
        """Tool call'ı işle ve sonucu geri gönder."""
        func_name = item.get("name", self.function_name)
        call_id = item.get("call_id", self.function_call_id)
        args_str = item.get("arguments", self.function_args)

        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args = {}
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ JSON parse hatası")

        logger.info(f"[{self.call_uuid[:8]}] 🔧 Tool: {func_name}({json.dumps(args, ensure_ascii=False)})")
        self.stats["tool_calls"] += 1

        result = handle_tool_call(self.call_uuid, func_name, args)

        await self.openai_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {"type": "function_call_output", "call_id": call_id, "output": result}
        }))
        await self.openai_ws.send(json.dumps({"type": "response.create"}))

        call_data = active_calls.get(self.call_uuid, {})
        if call_data.get("transfer_requested"):
            logger.info(f"[{self.call_uuid[:8]}] 🔄 Transfer istendi")

        # Agent requested call end → delayed hangup (wait for goodbye message)
        if call_data.get("end_call_requested"):
            logger.info(f"[{self.call_uuid[:8]}] 🔚 End call → delayed hangup (3s)")
            asyncio.create_task(self._delayed_hangup(3))

        self.function_name = ""
        self.function_args = ""
        self.function_call_id = ""

    async def _delayed_hangup(self, delay: float):
        """
        Agent end_call tool çağırdığında, veda mesajı için bekleyip sonra hangup yap.
        Delay süresi agent'ın veda mesajını söylemesine yeterli olmalı.
        """
        await asyncio.sleep(delay)
        if not self.is_active:
            return  # Already hung up (customer did it first)

        logger.info(f"[{self.call_uuid[:8]}] 🔚 Delayed hangup executing")
        self.sip_code = 200
        self.hangup_cause = "Agent End Call"
        self.is_active = False

        # 1. Send hangup to Asterisk
        try:
            self.writer.write(build_audiosocket_message(MSG_HANGUP))
            await self.writer.drain()
        except Exception:
            pass

        # 2. Close TCP writer → unblocks _asterisk_to_openai
        try:
            self.writer.close()
        except Exception:
            pass

        # 3. Close OpenAI WebSocket → unblocks _openai_to_asterisk
        try:
            if self.openai_ws and self.openai_ws.state == State.OPEN:
                await self.openai_ws.close()
        except Exception:
            pass

    async def _check_hangup_signal(self):
        """Check Redis for external hangup signal (from frontend/API).
        When signal is received, forcefully close all connections to unblock
        the other tasks that are waiting on I/O.
        """
        try:
            import redis.asyncio as redis_async
            r = redis_async.from_url(REDIS_URL, decode_responses=True)
            try:
                while self.is_active:
                    sig = await r.get(f"hangup_signal:{self.call_uuid}")
                    if sig:
                        logger.info(f"[{self.call_uuid[:8]}] 🛑 Redis hangup signal received - forcing disconnect")
                        await r.delete(f"hangup_signal:{self.call_uuid}")
                        self.sip_code = 200
                        self.hangup_cause = "User Hangup (Manual)"
                        self.is_active = False

                        # 1. Send hangup to Asterisk so the SIP call is terminated
                        try:
                            self.writer.write(build_audiosocket_message(MSG_HANGUP))
                            await self.writer.drain()
                        except Exception:
                            pass

                        # 2. Close the TCP writer → reader will get IncompleteReadError
                        try:
                            self.writer.close()
                        except Exception:
                            pass

                        # 3. Close OpenAI WebSocket → _openai_to_asterisk will get ConnectionClosed
                        try:
                            if self.openai_ws and self.openai_ws.state == State.OPEN:
                                await self.openai_ws.close()
                        except Exception:
                            pass

                        break
                    await asyncio.sleep(1)
            finally:
                await r.close()
        except Exception as e:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Hangup signal check error: {e}")

    async def _cleanup(self):
        """End-of-call cleanup and post-call processing."""
        duration = (datetime.now() - self.start_time).total_seconds()

        # Set default SIP code if not already set
        if not self.sip_code:
            self.sip_code = 200
            self.hangup_cause = self.hangup_cause or "Normal Clearing"

        logger.info(
            f"[{self.call_uuid[:8]}] 📊 Çağrı sonu: "
            f"süre={duration:.1f}s, "
            f"in={self.stats['audio_frames_in']}f/{self.stats['audio_bytes_in']}B, "
            f"out={self.stats['audio_frames_out']}f/{self.stats['audio_bytes_out']}B, "
            f"tools={self.stats['tool_calls']}, errors={self.stats['errors']}"
        )

        if self.openai_ws and self.openai_ws.state == State.OPEN:
            await self.openai_ws.close()

        try:
            self.writer.write(build_audiosocket_message(MSG_HANGUP))
            await self.writer.drain()
            self.writer.close()
        except Exception:
            pass

        call_data = active_calls.pop(self.call_uuid, {})
        
        # ================================================================
        # POST-CALL PROCESSING - Summary, sentiment, quality score to DB
        # ================================================================
        try:
            await self._save_post_call_data(call_data, duration)
        except Exception as e:
            logger.error(f"[{self.call_uuid[:8]}] ❌ Post-call processing hatası: {e}")
        
        if call_data.get("customer"):
            logger.info(f"[{self.call_uuid[:8]}] 📋 Müşteri: {json.dumps(call_data['customer'], ensure_ascii=False)}")
    
    async def _save_post_call_data(self, call_data: dict, duration: float):
        """
        Post-call data processing: save summary, sentiment, tags, quality score to DB.
        Updates the CallLog record with enriched data.
        """
        # Calculate call quality score
        quality_score = self._calculate_quality_score(call_data, duration)
        
        # Prepare update data
        sentiment = call_data.get("sentiment", "neutral")
        summary = call_data.get("summary", "")
        tags = call_data.get("tags", [])
        callback_scheduled = call_data.get("callback_scheduled")
        customer = call_data.get("customer", {})
        action_items = call_data.get("action_items", [])
        satisfaction = call_data.get("customer_satisfaction", "neutral")

        # ================================================================
        # TRANSCRIPT: Read from Redis and prepare for DB persistence
        # ================================================================
        transcription_text = ""
        try:
            import redis.asyncio as redis_async
            r = redis_async.from_url(REDIS_URL, decode_responses=True)
            try:
                transcript_key = f"call_transcript:{self.call_uuid}"
                raw_items = await r.lrange(transcript_key, 0, -1)
                if raw_items:
                    # Redis LPUSH stores newest first, reverse for chronological order
                    raw_items.reverse()
                    lines = []
                    for item in raw_items:
                        try:
                            entry = json.loads(item)
                            role = entry.get("role", "unknown")
                            content = entry.get("content", "")
                            if content.strip():
                                lines.append(f"[{role}]: {content}")
                        except json.JSONDecodeError:
                            pass
                    transcription_text = "\n".join(lines)
                    logger.info(f"[{self.call_uuid[:8]}] 📝 Transcript read from Redis: {len(lines)} messages")
            finally:
                await r.close()
        except Exception as t_err:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Transcript Redis read error: {t_err}")
        
        # Build metadata
        metadata = {
            "customer_data": customer,
            "quality_score": quality_score,
            "action_items": action_items,
            "customer_satisfaction": satisfaction,
            "sentiment_reason": call_data.get("sentiment_reason", ""),
            "callback_reason": call_data.get("callback_reason", ""),
            "callback_notes": call_data.get("callback_notes", ""),
            "transfer_requested": call_data.get("transfer_requested", False),
            "transfer_department": call_data.get("transfer_department", ""),
            "tool_calls_count": self.stats.get("tool_calls", 0),
            "errors_count": self.stats.get("errors", 0),
            "model_used": self.agent_model,
            "transcript_model": self.agent_transcript_model,
            "vad_type": self.agent_turn_detection,
        }
        
        # Save to Redis for immediate access
        try:
            import redis.asyncio as redis_async
            r = redis_async.from_url(REDIS_URL, decode_responses=True)
            try:
                post_call_key = f"call_postcall:{self.call_uuid}"
                await r.setex(post_call_key, 86400, json.dumps({
                    "sentiment": sentiment,
                    "summary": summary,
                    "tags": tags,
                    "quality_score": quality_score,
                    "callback_scheduled": callback_scheduled,
                    "metadata": metadata,
                    "duration": duration,
                }, ensure_ascii=False, default=str))
                logger.info(f"[{self.call_uuid[:8]}] 📊 Post-call data Redis'e kaydedildi (quality={quality_score})")
            finally:
                await r.close()
        except Exception as e:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Post-call Redis hatası: {e}")
        
        # Fetch token usage from Redis and calculate cost
        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0
        estimated_cost = 0.0
        model_used = self.agent_model or MODEL

        try:
            import redis.asyncio as redis_async
            r = redis_async.from_url(REDIS_URL, decode_responses=True)
            try:
                usage_data = await r.get(f"call_usage:{self.call_uuid}")
                if usage_data:
                    usage = json.loads(usage_data)
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    model_used = usage.get("model", model_used)

                    # Calculate cost from token details
                    pricing = COST_PER_TOKEN.get(model_used, COST_PER_TOKEN["gpt-realtime-mini"])

                    input_details = usage.get("input_token_details", {})
                    output_details = usage.get("output_token_details", {})

                    input_text = input_details.get("text_tokens", 0)
                    input_audio = input_details.get("audio_tokens", 0)
                    cached_text = input_details.get("cached_tokens", 0)
                    cached_audio = 0

                    # Handle cached_tokens_details if available
                    cached_details = input_details.get("cached_tokens_details", {})
                    if cached_details:
                        cached_text = cached_details.get("text_tokens", 0)
                        cached_audio = cached_details.get("audio_tokens", 0)

                    cached_tokens = cached_text + cached_audio

                    output_text = output_details.get("text_tokens", 0)
                    output_audio = output_details.get("audio_tokens", 0)

                    # If no details, estimate 80% text / 20% audio
                    if not input_details:
                        input_text = int(input_tokens * 0.8)
                        input_audio = input_tokens - input_text

                    if not output_details:
                        output_text = int(output_tokens * 0.8)
                        output_audio = output_tokens - output_text

                    # Uncached input tokens
                    uncached_text = max(0, input_text - cached_text)
                    uncached_audio = max(0, input_audio - cached_audio)

                    # Calculate cost
                    estimated_cost = (
                        uncached_text * pricing["input_text"] +
                        uncached_audio * pricing["input_audio"] +
                        cached_text * pricing["cached_input_text"] +
                        cached_audio * pricing["cached_input_audio"] +
                        output_text * pricing["output_text"] +
                        output_audio * pricing["output_audio"]
                    )

                    logger.info(
                        f"[{self.call_uuid[:8]}] 💰 Cost: ${estimated_cost:.6f} "
                        f"(in={input_tokens} out={output_tokens} cached={cached_tokens} model={model_used})"
                    )
            finally:
                await r.close()
        except Exception as e:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Usage/cost hesaplama hatası: {e}")

        # Save to PostgreSQL
        try:
            conn = await asyncpg.connect(
                host=DB_HOST, port=DB_PORT, user=DB_USER,
                password=DB_PASSWORD, database=DB_NAME,
            )
            try:
                # Try to update existing call_log by call_sid
                result = await conn.execute(
                    """UPDATE call_logs SET
                        sentiment = $1,
                        summary = $2,
                        tags = $3,
                        callback_scheduled = $4,
                        call_metadata = $5,
                        duration = $6,
                        notes = $7,
                        customer_name = $8,
                        sip_code = $9,
                        hangup_cause = $10,
                        model_used = $11,
                        input_tokens = $12,
                        output_tokens = $13,
                        cached_tokens = $14,
                        estimated_cost = $15,
                        transcription = CASE WHEN $17 = '' THEN transcription ELSE $17 END,
                        status = 'COMPLETED',
                        ended_at = NOW()
                    WHERE call_sid = $16""",
                    sentiment,
                    summary,
                    json.dumps(tags),
                    callback_scheduled,
                    json.dumps(metadata, default=str),
                    int(duration),
                    f"Quality Score: {quality_score}/100. {summary[:200] if summary else ''}",
                    customer.get("name", ""),
                    self.sip_code,
                    self.hangup_cause,
                    model_used,
                    input_tokens,
                    output_tokens,
                    cached_tokens,
                    estimated_cost,
                    self.call_uuid,
                    transcription_text,
                )
                if "UPDATE 0" in result:
                    logger.info(f"[{self.call_uuid[:8]}] CallLog not found, inserting new record")
                    await conn.execute(
                        """INSERT INTO call_logs (
                            call_sid, status, duration, sentiment, summary,
                            tags, callback_scheduled, call_metadata, notes,
                            customer_name, sip_code, hangup_cause,
                            to_number, agent_id, started_at, ended_at, created_at,
                            model_used, input_tokens, output_tokens, cached_tokens, estimated_cost,
                            transcription
                        ) VALUES (
                            $1, 'COMPLETED', $2, $3, $4,
                            $5, $6, $7, $8,
                            $9, $10, $11,
                            $12, $13, $14, $15, $14,
                            $16, $17, $18, $19, $20,
                            $21
                        )""",
                        self.call_uuid,
                        int(duration),
                        sentiment,
                        summary,
                        json.dumps(tags),
                        callback_scheduled,
                        json.dumps(metadata, default=str),
                        f"Quality Score: {quality_score}/100. {summary[:200] if summary else ''}",
                        customer.get("name", ""),
                        self.sip_code,
                        self.hangup_cause,
                        self.customer_name or "",
                        int(self.agent_id) if hasattr(self, 'agent_id') and self.agent_id else None,
                        self.start_time,
                        datetime.now(),
                        model_used,
                        input_tokens,
                        output_tokens,
                        cached_tokens,
                        estimated_cost,
                        transcription_text or None,
                    )
                    logger.info(f"[{self.call_uuid[:8]}] CallLog inserted successfully")

                # Create DialAttempt record if this call has a dial_attempt_id
                # The dial_attempt_id is set by the hopper-based autodialer
                try:
                    row = await conn.fetchrow(
                        "SELECT id, dial_attempt_id FROM call_logs WHERE call_sid = $1",
                        self.call_uuid,
                    )
                    if row and row["dial_attempt_id"]:
                        attempt_id = row["dial_attempt_id"]
                        # Map SIP code to a dial attempt result
                        sip = self.sip_code or 200
                        if sip == 200:
                            attempt_result = "connected"
                        elif sip == 486:
                            attempt_result = "busy"
                        elif sip in (480, 408):
                            attempt_result = "no_answer"
                        elif sip in (503, 502):
                            attempt_result = "congestion"
                        elif sip == 404:
                            attempt_result = "invalid_number"
                        else:
                            attempt_result = "failed"

                        await conn.execute(
                            """UPDATE dial_attempts SET
                                result = $1,
                                sip_code = $2,
                                hangup_cause = $3,
                                duration = $4,
                                call_log_id = $5,
                                ended_at = NOW()
                            WHERE id = $6""",
                            attempt_result,
                            self.sip_code,
                            self.hangup_cause,
                            int(duration),
                            row["id"],
                            attempt_id,
                        )
                        logger.info(
                            f"[{self.call_uuid[:8]}] DialAttempt #{attempt_id} updated: "
                            f"result={attempt_result}, sip={self.sip_code}"
                        )
                except Exception as da_err:
                    logger.warning(f"[{self.call_uuid[:8]}] DialAttempt update error: {da_err}")

            finally:
                await conn.close()
        except Exception as e:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Post-call DB hatası: {e}")

        # ================================================================
        # RECORDING: Save audio from Redis to MinIO
        # ================================================================
        try:
            from app.services.minio_service import minio_service
            recording_key = await minio_service.save_recording_from_redis(self.call_uuid)
            if recording_key:
                # Update call_log with recording URL
                try:
                    conn = await asyncpg.connect(
                        host=DB_HOST, port=DB_PORT, user=DB_USER,
                        password=DB_PASSWORD, database=DB_NAME,
                    )
                    try:
                        await conn.execute(
                            """UPDATE call_logs SET
                                recording_url = $1
                            WHERE call_sid = $2""",
                            recording_key,
                            self.call_uuid,
                        )
                        logger.info(f"[{self.call_uuid[:8]}] 🎙️ Recording URL saved to DB: {recording_key}")
                    finally:
                        await conn.close()
                except Exception as db_err:
                    logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Recording URL DB update failed: {db_err}")

                # Trigger transcription task if agent has record_calls enabled
                try:
                    from app.tasks.celery_tasks import transcribe_recording
                    if hasattr(self, 'agent_id') and self.agent_id:
                        conn2 = await asyncpg.connect(
                            host=DB_HOST, port=DB_PORT, user=DB_USER,
                            password=DB_PASSWORD, database=DB_NAME,
                        )
                        try:
                            row = await conn2.fetchrow(
                                "SELECT id FROM call_logs WHERE call_sid = $1",
                                self.call_uuid,
                            )
                            if row:
                                transcribe_recording.delay(row["id"])
                                logger.info(f"[{self.call_uuid[:8]}] 📝 Transcription task queued")
                        finally:
                            await conn2.close()
                except Exception as tx_err:
                    logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Transcription task queue failed: {tx_err}")
        except Exception as rec_err:
            logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Recording save failed: {rec_err}")

    def _calculate_quality_score(self, call_data: dict, duration: float) -> int:
        """
        Calculate a call quality score (0-100) based on multiple factors.
        
        Scoring breakdown:
        - Information completeness: 0-30 points
        - Customer sentiment: 0-25 points  
        - Call efficiency: 0-20 points
        - Tool usage success: 0-15 points
        - Error-free execution: 0-10 points
        """
        score = 0
        customer = call_data.get("customer", {})
        
        # 1. Information completeness (0-30 points)
        info_fields = ["name", "phone", "email", "address"]
        filled = sum(1 for f in info_fields if customer.get(f))
        score += int((filled / max(len(info_fields), 1)) * 30)
        
        # 2. Customer sentiment (0-25 points)
        sentiment_scores = {"positive": 25, "neutral": 15, "negative": 5}
        score += sentiment_scores.get(call_data.get("sentiment", "neutral"), 15)
        
        # 3. Call efficiency (0-20 points) — shorter effective calls are better
        satisfaction = call_data.get("customer_satisfaction", "neutral")
        satisfaction_scores = {
            "very_satisfied": 20, "satisfied": 16, "neutral": 10,
            "dissatisfied": 5, "very_dissatisfied": 0
        }
        score += satisfaction_scores.get(satisfaction, 10)
        
        # 4. Tool usage success (0-15 points)
        tool_calls = self.stats.get("tool_calls", 0)
        if tool_calls > 0:
            # Having successful tool calls is good
            score += min(tool_calls * 3, 15)
        
        # 5. Error-free execution (0-10 points)
        errors = self.stats.get("errors", 0)
        if errors == 0:
            score += 10
        elif errors <= 2:
            score += 5
        
        return min(score, 100)

    async def _update_conversation_phase(self, user_transcript: str):
        """
        Detect conversation phase transitions based on turn count and content.
        Sends session.update to adapt agent behavior if phase changes.
        
        Phases: opening → gathering → resolution (if needed) → closing
        """
        old_phase = self.conversation_phase
        transcript_lower = user_transcript.lower()
        
        # Phase detection logic
        # Complaint/problem keywords → resolution phase
        problem_keywords_tr = ["sorun", "problem", "şikayet", "çalışmıyor", "bozuk", "hata", "kızgın", "memnun değil", "sinirli"]
        problem_keywords_de = ["problem", "beschwerde", "funktioniert nicht", "kaputt", "fehler", "ärgerlich"]
        problem_keywords_en = ["problem", "complaint", "broken", "not working", "error", "angry", "upset"]
        
        # Closing keywords → closing phase
        closing_keywords_tr = ["teşekkür", "hoşçakal", "güle güle", "görüşürüz", "tamam bitti", "bu kadar"]
        closing_keywords_de = ["danke", "tschüss", "auf wiedersehen", "das war's", "fertig"]
        closing_keywords_en = ["thank you", "goodbye", "bye", "that's all", "done"]
        
        all_problem = problem_keywords_tr + problem_keywords_de + problem_keywords_en
        all_closing = closing_keywords_tr + closing_keywords_de + closing_keywords_en
        
        if any(kw in transcript_lower for kw in all_closing):
            self.conversation_phase = "closing"
        elif any(kw in transcript_lower for kw in all_problem):
            self.conversation_phase = "resolution"
        elif self.turn_count <= 2:
            self.conversation_phase = "opening"
        elif self.turn_count > 2:
            # After opening, move to gathering unless in resolution
            if self.conversation_phase == "opening":
                self.conversation_phase = "gathering"
        
        # Only update session if phase changed
        if old_phase != self.conversation_phase:
            logger.info(f"[{self.call_uuid[:8]}] 📋 Phase: {old_phase} → {self.conversation_phase}")
            
            # Publish phase change event for frontend
            asyncio.create_task(publish_event_to_redis(self.call_uuid, {
                "type": "conversation.phase.changed",
                "phase": self.conversation_phase,
                "turn_count": self.turn_count,
            }))

# ============================================================================
# TCP SERVER
# ============================================================================

active_call_count = 0


async def handle_audiosocket_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Yeni AudioSocket bağlantısını kabul et."""
    global active_call_count

    peer = writer.get_extra_info("peername")
    logger.info(f"🔗 Yeni bağlantı: {peer}")

    if active_call_count >= MAX_CONCURRENT_CALLS:
        logger.warning(f"⚠️ Max çağrı limiti ({MAX_CONCURRENT_CALLS})")
        writer.close()
        return

    active_call_count += 1
    call_uuid = None

    try:
        msg_type, payload = await asyncio.wait_for(
            read_audiosocket_message(reader), timeout=5.0
        )

        if msg_type != MSG_UUID:
            logger.error(f"❌ İlk mesaj UUID değil (0x{msg_type:02x})")
            writer.close()
            return

        if len(payload) == 16:
            call_uuid = str(uuid.UUID(bytes=payload))
        else:
            call_uuid = payload.decode("utf-8", errors="ignore").strip()

        if not call_uuid:
            call_uuid = str(uuid.uuid4())

        logger.info(f"[{call_uuid[:8]}] 📞 UUID: {call_uuid}")

        bridge = CallBridge(call_uuid, reader, writer)
        await bridge.start()

    except asyncio.TimeoutError:
        logger.error("❌ UUID timeout (5s)")
    except Exception as e:
        logger.error(f"❌ Bağlantı hatası: {e}")
    finally:
        active_call_count -= 1
        try:
            writer.close()
        except Exception:
            pass
        logger.info(f"[{call_uuid[:8] if call_uuid else '???'}] 📴 Kapandı (aktif: {active_call_count})")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    if OPENAI_API_KEY == "YOUR_API_KEY_HERE":
        logger.error("❌ OPENAI_API_KEY ayarlanmamış! → export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  Asterisk AudioSocket ↔ OpenAI Realtime Mini  (v4 Native 24kHz)║
║  MUTLU TELEKOM                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  AudioSocket  : {AUDIOSOCKET_HOST}:{AUDIOSOCKET_PORT:<40}║
║  Model        : {MODEL:<49}║
║  Max Calls    : {MAX_CONCURRENT_CALLS:<49}║
╠══════════════════════════════════════════════════════════════════╣
║  ★ Native 24kHz Passthrough                                   ║
║    Asterisk slin24 (0x13) ←→ OpenAI 24kHz PCM16                ║
║    Resampling yok, zero-copy passthrough                       ║
╠══════════════════════════════════════════════════════════════════╣
║  Optimizasyonlar:                                               ║
║    Temperature    : 0.6                                         ║
║    VAD            : semantic_vad (eagerness: low)               ║
║    Transcription  : gpt-4o-transcribe (DB-driven)               ║
║    Tools          : {len(_build_tools())} (from registry)                      ║
║    Features       : Sentiment, Memory, Callback, QualityScore   ║
╠══════════════════════════════════════════════════════════════════╣
║  pip install websockets                                         ║
║  Dialplan: Dial(AudioSocket/host:port/${{UUID}}/c(slin24))       ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    if AUDIOSOCKET_BIND != AUDIOSOCKET_HOST:
        logger.warning(
            "AUDIOSOCKET_HOST yerel bind icin uygun degil; bind 0.0.0.0 kullaniliyor. "
            "Istersen AUDIOSOCKET_BIND_HOST ayarla."
        )

    server = await asyncio.start_server(
        handle_audiosocket_connection, AUDIOSOCKET_BIND, AUDIOSOCKET_PORT
    )

    # TCP_NODELAY for low latency
    for sock in server.sockets:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    logger.info(f"🚀 Server bind: {AUDIOSOCKET_BIND}:{AUDIOSOCKET_PORT}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
