"""
Asterisk AudioSocket ↔ OpenAI Realtime Mini Bridge (v4 - Native 24kHz)
========================================================================
Asterisk'ten gelen çağrıyı AudioSocket protokolü ile alır,
OpenAI Realtime Mini WebSocket'e köprüler.

*** 24kHz PCM16 PASSTHROUGH ***
chan_audiosocket ile 24kHz slin24 (0x13) kullanılır.
OpenAI Realtime 24kHz PCM16 bekler.
Resampling yok - direkt aktarım.

Mimari:
    Telefon → SIP Trunk → Asterisk → AudioSocket (TCP:9092)
                                          ↕
                                  Bu Python Server (passthrough)
                                          ↕
                                    OpenAI Realtime API (WSS)

Ses Akışı (v4 - Native 24kHz):
    Asterisk (slin24) → 24kHz PCM16 → OpenAI Realtime
    OpenAI Realtime → 24kHz PCM16 → Asterisk (slin24)

Gereksinimler:
    pip install websockets

Asterisk Dialplan:
    Dial(AudioSocket/host:port/${UUID}/c(slin24))

Asterisk extensions.conf:
    [ai-agent]
    exten => 5001,1,Answer()
    exten => 5001,n,Set(UUID=${SHELL(cat /proc/sys/kernel/random/uuid | tr -d '\\n')})
    exten => 5001,n,Dial(AudioSocket/127.0.0.1:9092/${UUID}/c(slin24))
    exten => 5001,n,Hangup()

Kullanım:
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
from typing import Optional, Dict
from datetime import datetime

try:
    # websockets 16.x asyncio API
    from websockets.asyncio.client import connect as ws_connect
    from websockets.asyncio.client import ClientConnection
    from websockets.protocol import State  # state kontrolü için
    import websockets.exceptions
except ImportError:
    print("❌ websockets gerekli: pip install websockets")
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    print("❌ aiohttp gerekli: pip install aiohttp")
    sys.exit(1)

try:
    import asyncpg
except ImportError:
    print("❌ asyncpg gerekli: pip install asyncpg")
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
# YAPILANDIRMA
# ============================================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
MODEL = os.environ.get("REALTIME_MODEL", "gpt-realtime-mini")

# AudioSocket server ayarları
AUDIOSOCKET_HOST = os.environ.get("AUDIOSOCKET_HOST", "0.0.0.0")
AUDIOSOCKET_PORT = int(os.environ.get("AUDIOSOCKET_PORT", "9092"))
AUDIOSOCKET_BIND_HOST = os.environ.get("AUDIOSOCKET_BIND_HOST", "").strip()
LOCAL_BIND_HOSTS = {"0.0.0.0", "127.0.0.1", "::", "::1", "localhost"}

# Asterisk ARI ayarları (channel variables için)
ARI_HOST = os.environ.get("ASTERISK_HOST", "asterisk")
ARI_PORT = int(os.environ.get("ASTERISK_ARI_PORT", "8088"))
ARI_USERNAME = os.environ.get("ASTERISK_ARI_USER", "voiceai")
ARI_PASSWORD = os.environ.get("ASTERISK_ARI_PASSWORD", "voiceai_ari_secret")

# PostgreSQL ayarları (agent bilgileri için)
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres")
DB_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME = os.environ.get("POSTGRES_DB", "voiceai")
DB_USER = os.environ.get("POSTGRES_USER", "voiceai")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "voiceai_secret")

if AUDIOSOCKET_BIND_HOST:
    AUDIOSOCKET_BIND = AUDIOSOCKET_BIND_HOST
elif AUDIOSOCKET_HOST in LOCAL_BIND_HOSTS:
    AUDIOSOCKET_BIND = AUDIOSOCKET_HOST
else:
    AUDIOSOCKET_BIND = "0.0.0.0"

# Eşzamanlı çağrı limiti
MAX_CONCURRENT_CALLS = int(os.environ.get("MAX_CONCURRENT_CALLS", "50"))

# OpenAI WebSocket URL
OPENAI_WS_URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"

# ============================================================================
# SES FORMAT SABİTLERİ - Native 24kHz Passthrough
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
                "SELECT id, name, voice, model_type, language, prompt_role FROM agents WHERE id = $1",
                agent_id
            )
            
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "voice": row["voice"] or "ash",
                    "model_type": row["model_type"] or "gpt-4o-realtime-preview-2024-12-17",
                    "language": row["language"] or "tr",
                    "prompt_role": row["prompt_role"] or "",
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
# SYSTEM PROMPT - Mini Model İçin Optimize Edilmiş (Türkçe)
# ============================================================================

SYSTEM_INSTRUCTIONS = """
# Rol ve Amaç
- Sen MUTLU TELEKOM müşteri hizmetleri sesli asistanısın.
- Telefon üzerinden müşterilerle konuşuyorsun.
- Amacın müşteriden doğru bilgi toplamak ve kaydetmek.

# Kişilik ve Ton
## Kişilik
- Samimi, sakin ve profesyonel müşteri temsilcisi.

## Ton
- Sıcak, kısa ve özlü, kendinden emin.

## Uzunluk
- Her yanıtın EN FAZLA 2-3 cümle olsun.
- Telefon konuşmasında kısa ve net ol.

## Dil
- Bu görüşme YALNIZCA Türkçe yapılacaktır.
- Başka bir dilde ASLA yanıt verme.

## Çeşitlilik
- Aynı cümleyi iki kez tekrarlama.
- Onay verirken farklı ifadeler kullan: "Anladım", "Tamam", "Aldım", "Tamamdır".

# Telaffuz Rehberi
- "@" işaretini "et işareti" olarak söyle.
- ".com" ifadesini "nokta kom" olarak söyle.
- ".tr" ifadesini "nokta te-er" olarak söyle.

# Alfanümerik Telaffuz Kuralları
- Telefon numarası okurken HER RAKAMI TEK TEK, tire ile ayırarak söyle.
- Örnek: 0532 yerine "sıfır-beş-üç-iki" de.
- E-mail okurken HER HARFİ tek tek spell et.
- Okuduğun numarayı BİREBİR tekrarla, ASLA rakam ekleme veya çıkarma.

# Talimatlar ve Kurallar
## Numara ve Kod Toplama
- Telefon numarası, e-mail veya adres alırken İKİ AŞAMALI TEYİT uygula:
  1. Duyduğunu harf harf veya rakam rakam tekrarla
  2. Müşteriden onay al
  3. ONAY ALMADAN bir sonraki adıma ASLA geçme
- Anlamadığın kısmı TAHMIN ETME, tekrar sor.

## Anlaşılmayan Ses
- Ses net değilse veya arka plan gürültüsü varsa, nazikçe tekrar sor.
- "Özür dilerim, sizi tam anlayamadım. Tekrar eder misiniz?" de.

# Araçlar (Tools)
- Bir araç çağırmadan ÖNCE müşteriye kısa bilgi ver: "Kaydediyorum" gibi.

# Konuşma Akışı
1. Karşılama: Müşteriyi selamla
2. Bilgi Toplama: Ad-Soyad → Telefon → E-mail → Adres (sırasıyla, her biri için ayrı teyit)
3. Genel Teyit: Tüm bilgileri özetle
4. Kapanış: Teşekkür et
"""

# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

TOOLS = [
    {
        "type": "function",
        "name": "save_customer_name",
        "description": "Müşterinin ad ve soyadını kaydet. Müşteri onayladıktan SONRA çağır.",
        "parameters": {
            "type": "object",
            "properties": {
                "first_name": {"type": "string", "description": "Müşterinin adı"},
                "last_name": {"type": "string", "description": "Müşterinin soyadı"},
                "confirmed": {"type": "boolean", "description": "Müşteri onayladı mı"}
            },
            "required": ["first_name", "last_name", "confirmed"]
        }
    },
    {
        "type": "function",
        "name": "save_phone_number",
        "description": "Müşterinin telefon numarasını kaydet. Numarayı rakam rakam teyit ettikten ve onay aldıktan SONRA çağır. Sadece rakamlar.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string", "description": "Telefon numarası, sadece rakamlar: 05321234567"},
                "confirmed": {"type": "boolean", "description": "Müşteri onayladı mı"}
            },
            "required": ["phone_number", "confirmed"]
        }
    },
    {
        "type": "function",
        "name": "save_email",
        "description": "Müşterinin e-mail adresini kaydet. E-maili harf harf spell ederek teyit ettikten ve onay aldıktan SONRA çağır.",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "E-mail adresi, küçük harflerle"},
                "confirmed": {"type": "boolean", "description": "Müşteri onayladı mı"}
            },
            "required": ["email", "confirmed"]
        }
    },
    {
        "type": "function",
        "name": "save_address",
        "description": "Müşterinin adresini kaydet. Adresi özetleyip teyit ettikten ve onay aldıktan SONRA çağır.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Şehir"},
                "district": {"type": "string", "description": "İlçe"},
                "neighborhood": {"type": "string", "description": "Mahalle"},
                "street": {"type": "string", "description": "Sokak/cadde ve numara"},
                "building_no": {"type": "string", "description": "Bina no"},
                "apartment_no": {"type": "string", "description": "Daire no"},
                "confirmed": {"type": "boolean", "description": "Müşteri onayladı mı"}
            },
            "required": ["city", "district", "confirmed"]
        }
    },
    {
        "type": "function",
        "name": "complete_registration",
        "description": "Tüm bilgiler toplandıktan ve müşteri onay verdikten sonra kaydı tamamla.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Toplanan bilgilerin özeti"}
            },
            "required": ["summary"]
        }
    },
    {
        "type": "function",
        "name": "transfer_to_human",
        "description": "Müşteriyi yetkili birime/gerçek operatöre yönlendir. Müşteri istediğinde veya çözülemeyen durumlarda çağır.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Yönlendirme sebebi"},
                "department": {"type": "string", "description": "Hedef departman: destek, satis, teknik"}
            },
            "required": ["reason"]
        }
    }
]

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

        # Agent ayarları (default değerler)
        self.agent_voice = "ash"
        self.agent_model = MODEL  # gpt-realtime-mini veya gpt-realtime
        self.agent_language = "tr"
        self.agent_prompt = SYSTEM_INSTRUCTIONS
        self.customer_name = None

        # Audio buffer - küçük chunk'ları biriktirip toplu gönderim
        # 100ms = 5x 20ms chunk → kesik ses sorununu önler
        self.audio_buffer = bytearray()
        self.buffer_target_ms = 100  # 60→100ms arttırıldı
        self.buffer_target_bytes = ASTERISK_SAMPLE_RATE * 2 * self.buffer_target_ms // 1000
        
        # Output buffer - OpenAI'den gelen sesi düzgün akıtmak için
        self.output_buffer = bytearray()
        self.output_buffer_min_ms = 80  # 80ms buffer dolmadan çalmaya başlama

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

        # Agent ayarlarını ARI'den çek
        channel_vars = await get_channel_variables(self.call_uuid)
        
        # Agent ID varsa database'den bilgileri çek
        agent_id_str = channel_vars.get("VOICEAI_AGENT_ID")
        if agent_id_str:
            try:
                agent_id = int(agent_id_str)
                agent_data = await get_agent_from_db(agent_id)
                
                if agent_data:
                    self.agent_voice = agent_data["voice"]
                    self.agent_model = agent_data["model_type"]
                    self.agent_language = agent_data["language"]
                    self.agent_prompt = agent_data["prompt_role"] or SYSTEM_INSTRUCTIONS
                    
                    logger.info(f"[{self.call_uuid[:8]}] ✅ Agent '{agent_data['name']}' yüklendi: voice={self.agent_voice}, model={self.agent_model}, lang={self.agent_language}")
                else:
                    logger.warning(f"[{self.call_uuid[:8]}] ⚠️ Agent ID {agent_id} database'de bulunamadı, default ayarlar kullanılıyor")
            except Exception as e:
                logger.error(f"[{self.call_uuid[:8]}] ❌ Agent bilgileri alınamadı: {e}")
        
        # Customer name
        self.customer_name = channel_vars.get("VOICEAI_CUSTOMER_NAME")
        if self.customer_name:
            logger.info(f"[{self.call_uuid[:8]}] 👤 Müşteri ismi: {self.customer_name}")

        active_calls[self.call_uuid] = {
            "customer": {},
            "start_time": self.start_time.isoformat(),
            "transfer_requested": False,
        }

        try:
            await self._connect_openai()
            await self._configure_session()
            await asyncio.sleep(0.3)
            await self._trigger_greeting()

            await asyncio.gather(
                self._asterisk_to_openai(),
                self._openai_to_asterisk(),
            )
        except Exception as e:
            logger.error(f"[{self.call_uuid[:8]}] ❌ Hata: {e}")
            self.stats["errors"] += 1
        finally:
            await self._cleanup()

    async def _connect_openai(self):
        """OpenAI Realtime WebSocket'e bağlan."""
        # Model'i agent ayarından al
        openai_ws_url = f"wss://api.openai.com/v1/realtime?model={self.agent_model}"
        
        self.openai_ws = await ws_connect(
            openai_ws_url,
            additional_headers={  # websockets 16.x için additional_headers kullanılır
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1",  # ✅ ZORUNLU HEADER
            },
            ping_interval=20,
            ping_timeout=10,
            max_size=10 * 1024 * 1024,
        )
        logger.info(f"[{self.call_uuid[:8]}] 🔌 OpenAI bağlantısı kuruldu (model: {self.agent_model})")

    async def _configure_session(self):
        """OpenAI session'ını yapılandır - Agent ayarlarıyla."""
        # İsim varsa prompt'a ekle
        instructions = self.agent_prompt
        if self.customer_name:
            instructions = f"{instructions}\n\n# MÜŞTERİ BİLGİSİ\nMüşterinin ismi: {self.customer_name}\nMüşteriye ismini kullanarak hitap et."
        
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": self.agent_voice,  # Agent ayarından alınıyor
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "instructions": instructions,  # Agent ayarından alınıyor
                "temperature": 0.6,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.7,
                    "prefix_padding_ms": 500,
                    "silence_duration_ms": 800,
                    "create_response": True,
                },
                "input_audio_transcription": {
                    "model": "gpt-4o-mini-transcribe",
                    "language": self.agent_language,  # Agent ayarından alınıyor
                },
                "tools": TOOLS,
                "tool_choice": "auto",
                "max_response_output_tokens": 500,
            }
        }
        await self.openai_ws.send(json.dumps(config))
        logger.info(f"[{self.call_uuid[:8]}] ⚙️ Session yapılandırıldı: voice={self.agent_voice}, lang={self.agent_language}")

    async def _trigger_greeting(self):
        """İlk karşılama."""
        await self.openai_ws.send(json.dumps({
            "type": "response.create",
            "response": {
                "instructions": "Müşteriyi karşıla. 'Merhaba, MUTLU TELEKOM'a hoş geldiniz. Size nasıl yardımcı olabilirim?' gibi kısa bir selamlama yap."
            }
        }))

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

                if event_type == "session.created":
                    logger.info(f"[{self.call_uuid[:8]}] 🎙️ Realtime session hazır")

                elif event_type == "response.audio.delta":
                    audio_b64 = event.get("delta", "")
                    if audio_b64:
                        audio_pcm_24k = base64.b64decode(audio_b64)
                        self.output_buffer.extend(audio_pcm_24k)
                        
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
                
                elif event_type == "response.audio.done":
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

                elif event_type == "response.audio_transcript.done":
                    transcript = event.get("transcript", "")
                    if transcript:
                        logger.info(f"[{self.call_uuid[:8]}] 🤖 Agent: \"{transcript}\"")

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

        self.function_name = ""
        self.function_args = ""
        self.function_call_id = ""

    async def _cleanup(self):
        """Çağrı sonu temizlik."""
        duration = (datetime.now() - self.start_time).total_seconds()

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
        if call_data.get("customer"):
            logger.info(f"[{self.call_uuid[:8]}] 📋 Müşteri: {json.dumps(call_data['customer'], ensure_ascii=False)}")


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
║    VAD Threshold  : 0.7, Silence: 800ms                         ║
║    Transcription  : gpt-4o-mini-transcribe (Türkçe)             ║
║    Tools          : {len(TOOLS)} adet                                         ║
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
