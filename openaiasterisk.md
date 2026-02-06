# Asterisk + OpenAI Realtime API Ses Yapılandırması

**Versiyon:** v4 - Native 24kHz Passthrough  
**Tarih:** 5 Şubat 2026  
**Durum:** ✅ ÇALIŞIYOR  
**Proje:** MUTLU TELEKOM VoiceAI Platform

---

## 📋 İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Mimari](#mimari)
3. [Codec ve Ses Format Detayları](#codec-ve-ses-format-detayları)
4. [Asterisk Yapılandırması](#asterisk-yapılandırması)
5. [Python Bridge Yapılandırması](#python-bridge-yapılandırması)
6. [Docker Network Ayarları](#docker-network-ayarları)
7. [Kurulum Adımları](#kurulum-adımları)
8. [Doğrulama Komutları](#doğrulama-komutları)
9. [Sorun Giderme](#sorun-giderme)
10. [Önemli Notlar](#önemli-notlar)

---

## Genel Bakış

Bu sistem, Asterisk PBX ile OpenAI Realtime API arasında **24kHz PCM16 native passthrough** köprüsü kurar. Resampling yapılmaz, ses doğrudan aktarılır.

### Temel Bileşenler

| Bileşen | Teknoloji | Port |
|---------|-----------|------|
| PBX | Asterisk (Docker) | 5060 (SIP) |
| Bridge | Python 3.11 + websockets 16.x | 9092 (TCP) |
| AI | OpenAI Realtime API | WSS |
| Trunk | SIP (85.95.239.198) | 5060 |

---

## Mimari

```
┌─────────────────┐     SIP/RTP      ┌─────────────────────────────────────┐
│   SIP Trunk     │◄───────────────►│          Asterisk (Docker)          │
│ 85.95.239.198   │   ulaw/alaw      │   - PJSIP                           │
│ Account: 100    │                  │   - chan_audiosocket (24kHz slin24) │
└─────────────────┘                  └─────────────┬───────────────────────┘
                                                   │
                                                   │ AudioSocket TCP
                                                   │ Port 9092
                                                   │ 24kHz slin24 (0x13)
                                                   ▼
                        ┌──────────────────────────────────────────────────┐
                        │            Python Bridge (Windows Host)          │
                        │   - websockets 16.x                              │
                        │   - 24kHz PCM16 passthrough                      │
                        │   - Base64 encoding/decoding                     │
                        └─────────────┬────────────────────────────────────┘
                                      │
                                      │ WebSocket Secure (WSS)
                                      │ 24kHz PCM16 Base64
                                      ▼
                        ┌──────────────────────────────────────────────────┐
                        │              OpenAI Realtime API                 │
                        │   - Model: gpt-realtime-mini                     │
                        │   - input_audio_format: pcm16                    │
                        │   - output_audio_format: pcm16                   │
                        │   - 24kHz sample rate (native)                   │
                        └──────────────────────────────────────────────────┘
```

### Ses Akışı

```
[Telefon] → [SIP ulaw/alaw] → [Asterisk transcoding] → [slin24 24kHz]
                                                              ↓
                                                    [AudioSocket TCP]
                                                              ↓
                                                    [Python Bridge]
                                                              ↓
                                                    [Base64 encode]
                                                              ↓
                                                    [OpenAI WSS]
                                                              ↓
                                                    [AI Response]
                                                              ↓
                                                    [Base64 decode]
                                                              ↓
                                                    [Python Bridge]
                                                              ↓
                                                    [AudioSocket TCP]
                                                              ↓
                                              [slin24 24kHz] → [Asterisk transcoding]
                                                              ↓
                                              [SIP ulaw/alaw] → [Telefon]
```

---

## Codec ve Ses Format Detayları

### OpenAI Realtime API Gereksinimleri

| Parametre | Değer | Açıklama |
|-----------|-------|----------|
| Format | `pcm16` | 16-bit signed integer PCM |
| Sample Rate | **24000 Hz** | 24kHz (sabit, değiştirilemez) |
| Channels | Mono | Tek kanal |
| Byte Order | Little-endian | Intel byte order |
| Encoding | Base64 | WebSocket üzerinden |

### Asterisk AudioSocket Protokolü

| Message Type | Hex | Decimal | Açıklama |
|--------------|-----|---------|----------|
| HANGUP | 0x00 | 0 | Çağrı sonlandırma |
| UUID | 0x01 | 1 | Çağrı UUID'si |
| DTMF | 0x03 | 3 | DTMF tuş bildirimi |
| AUDIO_8K | 0x10 | 16 | 8kHz slin (fallback) |
| AUDIO_16K | 0x12 | 18 | 16kHz slin |
| **AUDIO_24K** | **0x13** | **19** | **24kHz slin ← KULLANILAN** |
| AUDIO_48K | 0x16 | 22 | 48kHz slin |
| ERROR | 0xFF | 255 | Hata mesajı |

### Chunk Boyutları (20ms)

| Sample Rate | Hesaplama | Chunk Size |
|-------------|-----------|------------|
| 24kHz | 24000 × 0.020 × 2 bytes | **960 bytes** |
| 8kHz | 8000 × 0.020 × 2 bytes | 320 bytes |

### Asterisk Codec Desteği

```
Asterisk'te slin24 mevcut:
ID 12 - audio - slin24 (16 bit Signed Linear PCM 24kHz)

Translation path:
ulaw → slin24: 17ms
slin24 → ulaw: 14.5ms
```

---

## Asterisk Yapılandırması

### extensions.conf

```ini
; ============================================================================
; GLOBAL DEĞİŞKENLER
; ============================================================================

[globals]
VOICEAI_APP=voiceai
; ⚠️ ÖNEMLİ: Bridge Windows host'ta çalışıyorsa host.docker.internal kullan
AUDIOSOCKET_HOST=host.docker.internal
AUDIOSOCKET_PORT=9092
AUDIOSOCKET_ADDR=${AUDIOSOCKET_HOST}:${AUDIOSOCKET_PORT}
VOICEAI_CALLERID=491754571258
SIP_TRUNK=trunk


; ============================================================================
; AI AGENT - 24kHz NATIVE
; ============================================================================

[ai-agent]
exten => 5001,1,Answer()
 same => n,Set(UUID=${SHELL(cat /proc/sys/kernel/random/uuid | tr -d '\n')})
 same => n,Set(CDR(ai_session)=${UUID})
 ; ⚠️ KRİTİK: c(slin24) parametresi 24kHz codec'i zorlar
 same => n,Dial(AudioSocket/${AUDIOSOCKET_ADDR}/${UUID}/c(slin24))
 same => n,Hangup()


; ============================================================================
; INBOUND - SIP Trunk'tan Gelen Çağrılar
; ============================================================================

[from-trunk]
exten => _X.,1,Answer()
 same => n,Wait(1)
 same => n,Set(UUID=${SHELL(cat /proc/sys/kernel/random/uuid | tr -d '\n')})
 same => n,Set(CDR(ai_session)=${UUID})
 same => n,Set(CDR(caller_id)=${CALLERID(num)})
 same => n,NoOp(AI Agent: ${UUID} | Arayan: ${CALLERID(num)})
 same => n,Dial(AudioSocket/${AUDIOSOCKET_ADDR}/${UUID}/c(slin24))
 same => n,Hangup()


; ============================================================================
; AI INBOUND - Outbound çağrılarda AI'a yönlendirme
; ============================================================================

[ai-inbound]
exten => s,1,Answer()
 same => n,Wait(1)
 same => n,Set(UUID=${SHELL(cat /proc/sys/kernel/random/uuid | tr -d '\n')})
 same => n,Set(CDR(ai_session)=${UUID})
 same => n,NoOp(AI Inbound: UUID=${UUID}, Caller=${CALLERID(num)})
 same => n,Dial(AudioSocket/${AUDIOSOCKET_ADDR}/${UUID}/c(slin24))
 same => n,Hangup()

exten => _X.,1,Goto(s,1)
```

### pjsip.conf

```ini
; ============================================================================
; SIP TRUNK YAPISI
; ============================================================================

[trunk]
type=endpoint
context=from-trunk
disallow=all
allow=ulaw          ; ← Trunk için ulaw codec
allow=alaw          ; ← Alternatif alaw
transport=transport-udp
outbound_auth=trunk-auth
aors=trunk-aor
direct_media=no
dtmf_mode=rfc4733
force_rport=yes
rewrite_contact=yes
rtp_symmetric=yes
from_user=100
from_domain=85.95.239.198
callerid="VoiceAI" <491754571258>
```

**NOT:** Trunk ulaw/alaw kullanır, Asterisk dahili olarak slin24'e transcode eder.

### Gerekli Asterisk Modülleri

```
app_audiosocket.so   - AudioSocket Application
chan_audiosocket.so  - AudioSocket Channel Driver  ← c(slin24) için gerekli
res_audiosocket.so   - AudioSocket Resource
```

---

## Python Bridge Yapılandırması

### Gereksinimler

```bash
pip install websockets>=16.0
```

### websockets 16.x API Değişiklikleri

**ESKİ (websockets 12.x):**
```python
from websockets import connect as ws_connect
from websockets.client import WebSocketClientProtocol as ClientConnection

ws = await ws_connect(url, extra_headers={...})
```

**YENİ (websockets 16.x):**
```python
from websockets.asyncio.client import connect as ws_connect
from websockets.asyncio.client import ClientConnection
from websockets.protocol import State

ws = await ws_connect(url, additional_headers={...})
```

### Kritik Kod Bölümleri

#### Import Tanımları
```python
try:
    # websockets 16.x asyncio API
    from websockets.asyncio.client import connect as ws_connect
    from websockets.asyncio.client import ClientConnection
    from websockets.protocol import State  # state kontrolü için
    import websockets.exceptions
except ImportError:
    print("❌ websockets gerekli: pip install websockets")
    sys.exit(1)
```

#### Ses Format Sabitleri
```python
# Native 24kHz - Resampling yok
ASTERISK_SAMPLE_RATE = 24000
OPENAI_SAMPLE_RATE = 24000
CHUNK_DURATION_MS = 20

# 24kHz chunk: 24kHz * 0.020s * 2 bytes = 960 bytes
ASTERISK_CHUNK_BYTES = 960
OPENAI_CHUNK_BYTES = 960

# AudioSocket protokol sabitleri
MSG_AUDIO_24K = 0x13  # ← Kullanılan format
```

#### OpenAI WebSocket Bağlantısı
```python
async def _connect_openai(self):
    self.openai_ws = await ws_connect(
        OPENAI_WS_URL,
        additional_headers={  # ⚠️ websockets 16.x için additional_headers
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1",  # ← ZORUNLU HEADER
        },
        ping_interval=20,
        ping_timeout=10,
        max_size=10 * 1024 * 1024,
    )
```

#### Session Yapılandırması
```python
async def _configure_session(self):
    config = {
        "type": "session.update",
        "session": {
            "modalities": ["text", "audio"],
            "voice": "ash",
            "input_audio_format": "pcm16",   # ← ZORUNLU
            "output_audio_format": "pcm16",  # ← ZORUNLU
            "instructions": SYSTEM_INSTRUCTIONS,
            "temperature": 0.6,
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.7,
                "prefix_padding_ms": 500,
                "silence_duration_ms": 300,
            },
            "tools": [...],
        }
    }
    await self.openai_ws.send(json.dumps(config))
```

---

## Docker Network Ayarları

### Senaryo: Bridge Windows Host'ta Çalışıyor

Asterisk Docker container'da, Python bridge Windows host'ta çalışırken:

```
Docker Container (Asterisk) → host.docker.internal → Windows Host (Bridge)
```

#### extensions.conf Ayarı
```ini
[globals]
; Bridge Windows host'ta çalışıyor
AUDIOSOCKET_HOST=host.docker.internal
AUDIOSOCKET_PORT=9092
AUDIOSOCKET_ADDR=${AUDIOSOCKET_HOST}:${AUDIOSOCKET_PORT}
```

#### DNS Çözümlemesi Doğrulama
```bash
docker exec voiceai-platform-asterisk-1 getent hosts host.docker.internal
# Çıktı: 192.168.65.254  host.docker.internal
```

### Alternatif: Bridge Docker Container'da Çalışıyor

```ini
[globals]
AUDIOSOCKET_HOST=asterisk-bridge  ; ← Docker service name
AUDIOSOCKET_PORT=9092
```

---

## Kurulum Adımları

### 1. Python Bağımlılıkları

```powershell
pip install websockets>=16.0
```

### 2. Asterisk Yapılandırması

```powershell
# extensions.conf kopyala
docker cp d:\openai\voiceai-platform\asterisk\extensions.conf voiceai-platform-asterisk-1:/etc/asterisk/extensions.conf

# pjsip.conf kopyala
docker cp d:\openai\voiceai-platform\asterisk\pjsip.conf voiceai-platform-asterisk-1:/etc/asterisk/pjsip.conf

# Reload
docker exec voiceai-platform-asterisk-1 asterisk -rx "dialplan reload"
docker exec voiceai-platform-asterisk-1 asterisk -rx "pjsip reload"
```

### 3. Bridge Başlatma

```powershell
$env:OPENAI_API_KEY="sk-proj-xxx"
$env:PYTHONIOENCODING="utf-8"
python D:\openai\voiceai-platform\backend\app\services\asterisk_bridge.py
```

### 4. Test Çağrısı

```powershell
# Dahili test
docker exec voiceai-platform-asterisk-1 asterisk -rx "channel originate Local/5001@ai-agent application Wait 10"

# Dış arama
docker exec voiceai-platform-asterisk-1 asterisk -rx "channel originate PJSIP/4921666846161@trunk application Dial Local/s@ai-inbound"
```

---

## Doğrulama Komutları

### Asterisk Kontrolleri

```bash
# Codec listesi - slin24 mevcut mu?
docker exec voiceai-platform-asterisk-1 asterisk -rx "core show codecs" | grep slin24

# Translation path
docker exec voiceai-platform-asterisk-1 asterisk -rx "core show translation" | grep slin24

# AudioSocket modülleri
docker exec voiceai-platform-asterisk-1 asterisk -rx "module show like audiosocket"
# Beklenen çıktı:
# app_audiosocket.so   Running
# chan_audiosocket.so  Running  ← c(slin24) için gerekli
# res_audiosocket.so   Running

# Global değişkenler
docker exec voiceai-platform-asterisk-1 asterisk -rx "dialplan show globals" | grep AUDIOSOCKET

# Dialplan kontrolü
docker exec voiceai-platform-asterisk-1 asterisk -rx "dialplan show ai-inbound"

# Aktif kanallar
docker exec voiceai-platform-asterisk-1 asterisk -rx "core show channels"

# PJSIP trunk durumu
docker exec voiceai-platform-asterisk-1 asterisk -rx "pjsip show registrations"
```

### Bridge Kontrolleri

```powershell
# Port dinleniyor mu?
netstat -an | Select-String "9092"

# Beklenen log çıktısı:
# 🚀 Server bind: 0.0.0.0:9092
# 🔗 Yeni bağlantı: ('127.0.0.1', xxxxx)
# [xxxxxxxx] 📞 Çağrı başlatılıyor...
# [xxxxxxxx] 🔌 OpenAI bağlantısı kuruldu (model: gpt-realtime-mini)
# [xxxxxxxx] ⚙️ Session yapılandırıldı (24kHz pcm16, temp=0.6, vad=0.7)
# [xxxxxxxx] 🎵 Audio: 24kHz (chunk=960B)  ← ÖNEMLİ: 960B olmalı
```

---

## Sorun Giderme

### Hata: "extra_headers" keyword argument

**Sebep:** websockets 16.x API değişikliği

**Çözüm:**
```python
# ESKİ
extra_headers={...}

# YENİ
additional_headers={...}
```

### Hata: Bridge'e bağlanamıyor

**Sebep:** Docker container Windows host'a ulaşamıyor

**Çözüm:**
```ini
; extensions.conf
AUDIOSOCKET_HOST=host.docker.internal
```

### Hata: Audio: 8kHz (chunk=320B)

**Sebep:** c(slin24) parametresi eksik veya yanlış

**Çözüm:**
```ini
; Dialplan'da c(slin24) kullanıldığından emin ol
Dial(AudioSocket/${AUDIOSOCKET_ADDR}/${UUID}/c(slin24))
```

### Hata: Ses bozuk/robotik

**Olası sebepler:**
1. Resampling hatası - 24kHz native kullanılmalı
2. Buffer overflow - chunk boyutları kontrol edilmeli
3. Network latency - jitter buffer ayarları

**Kontrol:**
```
Bridge logu: 🎵 Audio: 24kHz (chunk=960B)
960 bytes = doğru 24kHz chunk
320 bytes = yanlış 8kHz chunk (resampling gerekli)
```

### Hata: chan_audiosocket.so yüklü değil

```bash
docker exec voiceai-platform-asterisk-1 asterisk -rx "module load chan_audiosocket.so"
```

---

## Önemli Notlar

### ⚠️ Kritik Yapılandırma Noktaları

1. **Dial() parametresi:** `c(slin24)` mutlaka olmalı
   ```
   Dial(AudioSocket/host:port/uuid/c(slin24))
   ```

2. **websockets versiyonu:** 16.x için `additional_headers` kullan

3. **OpenAI Header:** `OpenAI-Beta: realtime=v1` zorunlu

4. **Docker network:** Windows host için `host.docker.internal`

5. **Chunk boyutu:** 960 bytes (24kHz × 20ms × 2 bytes)

### 📊 Başarılı Çağrı Log Örneği

```
2026-02-05 20:19:11 [INFO] 🔗 Yeni bağlantı: ('127.0.0.1', 52682)
2026-02-05 20:19:11 [INFO] [193fb96b] 📞 UUID: 193fb96b-833d-4ea3-b44a-2c7fa9a9a65b
2026-02-05 20:19:11 [INFO] [193fb96b] 📞 Çağrı başlatılıyor...
2026-02-05 20:19:12 [INFO] [193fb96b] 🔌 OpenAI bağlantısı kuruldu (model: gpt-realtime-mini)
2026-02-05 20:19:12 [INFO] [193fb96b] ⚙️ Session yapılandırıldı (24kHz pcm16, temp=0.6, vad=0.7)
2026-02-05 20:19:12 [INFO] [193fb96b] 🎙️ Realtime session hazır
2026-02-05 20:19:13 [INFO] [193fb96b] 🎵 Audio: 24kHz (chunk=960B)  ← DOĞRU
2026-02-05 20:19:17 [INFO] [193fb96b] 🤖 Agent: "Merhaba, MUTLU TELEKOM'a hoş geldiniz..."
2026-02-05 20:19:17 [INFO] [193fb96b] 🗣️ Müşteri: "Hallo?"
```

### 📁 Dosya Konumları

| Dosya | Konum |
|-------|-------|
| Bridge | `backend/app/services/asterisk_bridge.py` |
| Dialplan | `asterisk/extensions.conf` |
| PJSIP | `asterisk/pjsip.conf` |
| Bu döküman | `openaiasterisk.md` |

---

## Versiyon Geçmişi

| Tarih | Versiyon | Değişiklik |
|-------|----------|------------|
| 2026-02-05 | v4 | Native 24kHz passthrough, websockets 16.x uyumu |

---

**Hazırlayan:** Cenani - MUTLU TELEKOM  
**Son Güncelleme:** 5 Şubat 2026, 20:25
