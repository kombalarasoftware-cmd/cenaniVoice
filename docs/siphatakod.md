# SIP Hata Kodu Yönetimi — VoiceAI Platform

> **Son Güncelleme:** 13 Şubat 2026  
> **Durum:** Tüm SIP hata kodları Ultravox ve diğer providerlar (OpenAI, xAI, Gemini) için hatasız çalışıyor.
> 
> **Bu doküman aynı zamanda yeni bir projede Asterisk + AI Provider (Ultravox, OpenAI vb.) entegrasyonunu sıfırdan kurmak için adım adım rehber niteliğindedir.**

---

## İçindekiler

**BÖLÜM A — SIFIRDAN KURULUM REHBERİ**

A1. [Ön Gereksinimler & Checklist](#a1-ön-gereksinimler--checklist)  
A2. [Adım 1: Asterisk Kurulumu (Docker)](#a2-adım-1-asterisk-kurulumu-docker)  
A3. [Adım 2: PJSIP Konfigürasyonu](#a3-adım-2-pjsip-konfigürasyonu)  
A4. [Adım 3: Dialplan Konfigürasyonu](#a4-adım-3-dialplan-konfigürasyonu)  
A5. [Adım 4: AMD Konfigürasyonu](#a5-adım-4-amd-konfigürasyonu)  
A6. [Adım 5: Backend Entegrasyonu](#a6-adım-5-backend-entegrasyonu)  
A7. [Adım 6: Environment Variables](#a7-adım-6-environment-variables)  
A8. [Adım 7: Test & Doğrulama](#a8-adım-7-test--doğrulama)  
A9. [Troubleshooting — Sık Karşılaşılan Hatalar](#a9-troubleshooting--sık-karşılaşılan-hatalar)  
A10. [Öğrenilen Dersler (Lessons Learned)](#a10-öğrenilen-dersler-lessons-learned)

**BÖLÜM B — TEKNİK REFERANS (MEVCUT SİSTEM)**

1. [Genel Mimari](#1-genel-mimari)
2. [CallLog Modeli — SIP Alanları](#2-calllog-modeli--sip-alanları)
3. [SIP Code Mapping Tabloları](#3-sip-code-mapping-tabloları)
4. [Ultravox Provider — SIP Hata Yönetimi](#4-ultravox-provider--sip-hata-yönetimi)
5. [OpenAI / xAI / Gemini Provider — SIP Hata Yönetimi](#5-openai--xai--gemini-provider--sip-hata-yönetimi)
6. [Asterisk Dialplan — SIP ve AMD İşleme](#6-asterisk-dialplan--sip-ve-amd-i̇şleme)
7. [Backend Webhook Endpoint'leri](#7-backend-webhook-endpointleri)
8. [Senaryo Bazlı Akış Diyagramları](#8-senaryo-bazlı-akış-diyagramları)
9. [SIP Code Referans Tablosu](#9-sip-code-referans-tablosu)
10. [Yapılan Geliştirmeler — Kronolojik](#10-yapılan-geliştirmeler--kronolojik)
11. [Dosya Referansları](#11-dosya-referansları)

---

# BÖLÜM A — SIFIRDAN KURULUM REHBERİ

> Bu bölüm, yeni bir projede Asterisk + Ultravox/OpenAI SIP entegrasyonunu sıfırdan kurmak için adım adım talimatlar içerir. Copilot'a bu dosyayı okutursan, sistemi hatasız kurabilir.

---

## A1. Ön Gereksinimler & Checklist

### Neye İhtiyacın Var?

| # | Gereksinim | Nereden Alınır | Notlar |
|---|-----------|----------------|--------|
| 1 | **VPS / Sunucu** | Hetzner, DigitalOcean, AWS vb. | Min 2 vCPU, 4GB RAM. Public IP gerekli. |
| 2 | **Domain** | Herhangi bir domain sağlayıcı | A Record → VPS IP. SSL için gerekli. |
| 3 | **SIP Trunk** | VoIP sağlayıcı (sipgate, Twilio, MUTLU TELEKOM vb.) | Host, port, username, password, CallerID bilgileri |
| 4 | **Ultravox API Key** | [app.ultravox.ai](https://app.ultravox.ai) | Hesap oluştur → API key al |
| 5 | **OpenAI API Key** | [platform.openai.com](https://platform.openai.com) | Realtime API erişimi gerekli |
| 6 | **Docker & Docker Compose** | Sunucuda kurulu | v24+ önerilir |

### Kurulum Öncesi Checklist

- [ ] Sunucu public IP'si not edildi
- [ ] SIP trunk bilgileri alındı (host, port, username, password, CallerID)
- [ ] Ultravox API key alındı
- [ ] Firewall açıldı: SIP port (5043/udp+tcp), RTP portları (10000-10100/udp), HTTP (8088/tcp)
- [ ] Domain DNS ayarlandı (A Record → sunucu IP)
- [ ] SSL sertifikası hazır (Let's Encrypt veya başka)

---

## A2. Adım 1: Asterisk Kurulumu (Docker)

### Asterisk Dockerfile

Asterisk 20 kaynak koddan derlenir. Aşağıdaki modüller **mutlaka** etkinleştirilmelidir:

```dockerfile
# Zorunlu modüller (menuselect ile):
menuselect/menuselect --enable chan_audiosocket    # AudioSocket channel driver
menuselect/menuselect --enable app_audiosocket     # AudioSocket application
menuselect/menuselect --enable res_ari             # ARI REST API
menuselect/menuselect --enable res_ari_channels    # ARI channel management
menuselect/menuselect --enable res_ari_bridges     # ARI bridge management
menuselect/menuselect --enable res_http_websocket  # WebSocket support
# + diğer res_ari_* ve res_stasis_* modülleri
```

> **UYARI:** `codec_opus` menuselect'e eklense bile Asterisk'in opus transcoder'ı yoktur! Opus sadece aynı codec'li iki uç arasında passthrough yapabilir. Farklı codec'ler arası çeviremez.

### docker-compose.yml Asterisk bölümü

```yaml
asterisk:
  build:
    context: ./asterisk
    dockerfile: Dockerfile
  container_name: voiceai-asterisk
  environment:
    - EXTERNAL_IP=${EXTERNAL_IP}           # Sunucu public IP
    - SIP_TRUNK_PASSWORD=${SIP_TRUNK_PASSWORD}
    - ULTRAVOX_SIP_PASSWORD=${ULTRAVOX_SIP_PASSWORD}
  ports:
    - "5043:5043/udp"    # SIP UDP
    - "5043:5043/tcp"    # SIP TCP
    - "8088:8088/tcp"    # ARI HTTP
    - "10000-10100:10000-10100/udp"  # RTP media
  networks:
    - voiceai-network
  restart: unless-stopped
```

### Doğrulama Komutları

```bash
# Asterisk çalışıyor mu?
docker exec voiceai-asterisk asterisk -rx "core show version"

# Modüller yüklü mü?
docker exec voiceai-asterisk asterisk -rx "module show like audiosocket"
docker exec voiceai-asterisk asterisk -rx "module show like amd"
docker exec voiceai-asterisk asterisk -rx "module show like ari"

# Dialplan yüklendi mi?
docker exec voiceai-asterisk asterisk -rx "dialplan show from-ultravox"
docker exec voiceai-asterisk asterisk -rx "dialplan show ai-outbound"

# PJSIP trunk kaydı aktif mi?
docker exec voiceai-asterisk asterisk -rx "pjsip show registrations"
docker exec voiceai-asterisk asterisk -rx "pjsip show endpoints"
```

---

## A3. Adım 2: PJSIP Konfigürasyonu

### Tam pjsip.conf Şablonu (Kopyala-Yapıştır)

```ini
; ===========================================================
; pjsip.conf — Yeni Proje Şablonu
; DEĞİŞTİRİLECEK YERLERİ BUL: __DEGISTIR__ ile işaretli
; ===========================================================

; --- Transport ---
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5043
external_signaling_address=__DEGISTIR_SUNUCU_PUBLIC_IP__
external_media_address=__DEGISTIR_SUNUCU_PUBLIC_IP__
local_net=172.16.0.0/12
local_net=10.0.0.0/8
local_net=192.168.0.0/16

; --- SIP Trunk Kaydı (Registration) ---
; Asterisk, SIP sağlayıcıya register olur
[trunk-reg]
type=registration
transport=transport-udp
outbound_auth=trunk-auth
server_uri=sip:__DEGISTIR_SIP_HOST__:__DEGISTIR_SIP_PORT__
client_uri=sip:__DEGISTIR_SIP_USERNAME__@__DEGISTIR_SIP_HOST__:__DEGISTIR_SIP_PORT__
contact_user=__DEGISTIR_SIP_USERNAME__
retry_interval=60
expiration=300
line=yes
endpoint=trunk

; --- SIP Trunk Auth ---
[trunk-auth]
type=auth
auth_type=userpass
username=__DEGISTIR_SIP_USERNAME__
password=__DEGISTIR_SIP_PASSWORD__
realm=__DEGISTIR_SIP_REALM__

; --- SIP Trunk AOR ---
[trunk-aor]
type=aor
contact=sip:__DEGISTIR_SIP_HOST__:__DEGISTIR_SIP_PORT__
qualify_frequency=30
qualify_timeout=3

; --- SIP Trunk Endpoint ---
[trunk]
type=endpoint
context=from-trunk
disallow=all
allow=ulaw
allow=alaw
transport=transport-udp
outbound_auth=trunk-auth
aors=trunk-aor
direct_media=no
dtmf_mode=rfc4733
force_rport=yes
ice_support=no
rewrite_contact=yes
rtp_symmetric=yes
send_pai=yes
send_rpid=yes
from_user=__DEGISTIR_SIP_USERNAME__
from_domain=__DEGISTIR_SIP_HOST__
callerid="VoiceAI" <__DEGISTIR_CALLERID__>

[trunk-identify]
type=identify
endpoint=trunk
match=__DEGISTIR_SIP_HOST__

; --- Ultravox SIP Endpoint (Ultravox Cloud → Asterisk) ---
; Ultravox bu credentials ile SIP INVITE gönderir
[ultravox-auth]
type=auth
auth_type=userpass
username=ultravox
password=__DEGISTIR_ULTRAVOX_SIP_PASSWORD__

[ultravox-aor]
type=aor
max_contacts=50

[ultravox]
type=endpoint
context=from-ultravox
disallow=all
; ÖNEMLİ: opus KULLANMA! Asterisk opus transcode edemez.
; Ultravox g722'ye fallback yapar (yüksek kalite, 16kHz).
allow=g722
allow=ulaw
allow=alaw
transport=transport-udp
auth=ultravox-auth
aors=ultravox-aor
direct_media=no
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes
dtmf_mode=rfc4733
ice_support=no

; --- Global ---
[global]
type=global
max_forwards=70
user_agent=VoiceAI-Asterisk/1.0
default_outbound_endpoint=trunk
endpoint_identifier_order=ip,username
```

### Kritik Kurallar

| Kural | Neden | Ne Olur Yapmazsan |
|-------|-------|-------------------|
| `opus codec KULLANMA` | Asterisk opus transcode edemez | "No path to translate from PJSIP/ultravox to PJSIP/trunk" hatası |
| `external_signaling_address` doğru olmalı | NAT arkasında SIP routing bozulur | SIP INVITE tek yönlü, ses gelmez |
| `direct_media=no` | Docker container'da direct media çalışmaz | Tek yönlü ses veya ses yok |
| `endpoint_identifier_order=ip,username` | Ultravox IP'si bilinmez, username ile tanınmalı | Çağrılar "Endpoint not found" ile reddedilir |
| `context=from-ultravox` | Ultravox çağrıları bu dialplan'a gider | Çağrılar başka context'e düşer, kaybolur |

---

## A4. Adım 3: Dialplan Konfigürasyonu

### Ultravox İçin Minimum Viable Dialplan

```ini
; extensions.conf — Ultravox entegrasyonu için minimum gerekli bölümler

[globals]
VOICEAI_CALLERID=__DEGISTIR_CALLERID__
SIP_TRUNK=trunk

; --- Ultravox'tan gelen çağrıları trunk'a yönlendir ---
[from-ultravox]
; +XX ile başlayan numaralar (en yaygın format)
exten => _+X.,1,NoOp(Ultravox bridge call to ${EXTEN})
 same => n,Set(CALLERID(num)=${VOICEAI_CALLERID})
 same => n,Set(CALLERID(name)=VoiceAI)
 same => n,Set(_ULTRAVOX_PHONE=${EXTEN})
 same => n,Dial(PJSIP/${EXTEN:1}@${SIP_TRUNK},120,gU(ultravox-amd-check,s,1))
 same => n,Hangup()

; 00XX ile başlayan (international format)
exten => _00X.,1,NoOp(Ultravox bridge international to ${EXTEN})
 same => n,Set(CALLERID(num)=${VOICEAI_CALLERID})
 same => n,Set(CALLERID(name)=VoiceAI)
 same => n,Set(_ULTRAVOX_PHONE=+${EXTEN:2})
 same => n,Dial(PJSIP/${EXTEN}@${SIP_TRUNK},120,gU(ultravox-amd-check,s,1))
 same => n,Hangup()

; Sadece rakamlar (+ prefix olmayan)
exten => _X.,1,NoOp(Ultravox bridge call to ${EXTEN})
 same => n,Set(CALLERID(num)=${VOICEAI_CALLERID})
 same => n,Set(CALLERID(name)=VoiceAI)
 same => n,Set(_ULTRAVOX_PHONE=+${EXTEN})
 same => n,Dial(PJSIP/${EXTEN}@${SIP_TRUNK},120,gU(ultravox-amd-check,s,1))
 same => n,Hangup()

; --- AMD Subroutine (Dial U() option ile çağrılır) ---
; Karşı taraf CEVAPLADIKTAN SONRA, bridge kurulmadan ÖNCE çalışır
[ultravox-amd-check]
exten => s,1,NoOp(Ultravox AMD check for ${ULTRAVOX_PHONE})
 same => n,AMD()
 same => n,NoOp(Ultravox AMD Result: ${AMDSTATUS} - ${AMDCAUSE})
 same => n,GotoIf($["${AMDSTATUS}" = "MACHINE"]?machine)
 same => n,GotoIf($["${AMDSTATUS}" = "NOTSURE"]?machine)
 ; HUMAN → Return() → Dial() bridge kurar → Ultravox AI konuşur
 same => n,Return()
 same => n(machine),NoOp(Ultravox AMD: ${AMDSTATUS} for ${ULTRAVOX_PHONE})
 same => n,System(curl -s -X POST http://backend:8000/api/v1/webhooks/amd-result \
   -H "Content-Type: application/json" \
   -d '{"phone":"${ULTRAVOX_PHONE}","status":"${AMDSTATUS}","cause":"${AMDCAUSE}","source":"ultravox"}' &)
 same => n,Set(GOSUB_RESULT=ABORT)
 same => n,Return()
```

### OpenAI / xAI / Gemini İçin Minimum Dialplan

```ini
; --- Backend ARI ile çağrı başlatır → Cevaplandıktan sonra AMD → AI bridge ---
[ai-outbound]
exten => s,1,Answer()
 same => n,ExecIf($["${VOICEAI_UUID}" = ""]?Set(VOICEAI_UUID=${SHELL(cat /proc/sys/kernel/random/uuid | tr -d '\n')}))
 same => n,Set(CDR(ai_session)=${VOICEAI_UUID})
 same => n,AMD()
 same => n,NoOp(AMD Result: ${AMDSTATUS} - ${AMDCAUSE})
 same => n,GotoIf($["${AMDSTATUS}" = "MACHINE"]?amd_machine,s,1)
 same => n,GotoIf($["${AMDSTATUS}" = "NOTSURE"]?amd_machine,s,1)
 ; HUMAN → AI agent'a bağla
 same => n,Dial(AudioSocket/${AUDIOSOCKET_ADDR}/${VOICEAI_UUID}/c(slin24))
 same => n,Hangup()

; --- AMD makine tespit — webhook + hangup ---
[amd_machine]
exten => s,1,NoOp(AMD Machine Detected: UUID=${VOICEAI_UUID})
 same => n,System(curl -s -X POST http://backend:8000/api/v1/webhooks/amd-result \
   -H "Content-Type: application/json" \
   -d '{"uuid":"${VOICEAI_UUID}","status":"${AMDSTATUS}","cause":"${AMDCAUSE}"}' &)
 same => n,Hangup()
```

### Dial() Parametre Rehberi

| Parametre | Açıklama | Ne Zaman Kullanılır |
|-----------|----------|---------------------|
| `g` | Dial() sonrası dialplan'a devam et | Hangup event processing için |
| `U(sub,ext,pri)` | Subroutine: cevaptan SONRA, bridge'den ÖNCE | AMD için (Ultravox çağrılarında) |
| `120` | Timeout (saniye) | Çalma süresi limiti |
| `${EXTEN:1}` | EXTEN'in 1. karakterden sonrasını al | `+49155...` → `49155...` (+ kaldır) |
| `${EXTEN:2}` | EXTEN'in 2. karakterden sonrasını al | `0049155...` → `49155...` (00 kaldır) |

### `_ULTRAVOX_PHONE` Değişkeni Neden Önemli?

- `_` prefix'i = channel variable → child channel'a (outbound leg) miras geçer
- AMD subroutine child channel'da çalışır → ana kanalın `${EXTEN}` değerine erişemez
- `_ULTRAVOX_PHONE` ile telefon numarası child channel'a iletilir → webhook'a gönderilir

---

## A5. Adım 4: AMD Konfigürasyonu

### Önerilen amd.conf (Test Edilmiş, Çalışan)

```ini
; amd.conf — Voicemail / Telesekreter Algılama
; Türk ve Alman ağları için optimize edilmiş değerler

[general]
; Toplam analiz süresi. Aşılırsa → NOTSURE
total_analysis_time = 3500

; Sessizlik eşiği (0-32767). Altı = sessiz.
silence_threshold = 256

; Greeting öncesi max sessizlik. Çok kısaysa insanlar yanlışlıkla MACHINE olur!
; ÖNERİ: 3000-3500 ms (bilinmeyen numaralarda insanlar geç cevap verir)
initial_silence = 3500

; Greeting sonrası sessizlik → HUMAN
; ÖNERİ: 400-600 ms (kişi "Alo" deyip susar → hızlıca HUMAN kararı)
after_greeting_silence = 500

; Max greeting uzunluğu. Aşılırsa → MACHINE (uzun kayıtlı mesaj)
; ÖNERİ: 2500-3000 ms (Türkçe/Almanca selamlamalar 2+ sn sürebilir)
greeting = 3000

; Kelime tespiti parametreleri
min_word_length = 100
maximum_word_length = 5000
between_words_silence = 50

; Max kelime sayısı. Aşılırsa → MACHINE
; ÖNERİ: 4-6 (voicemail genelde 6+ kelime, "Alo buyurun kimsiniz" = 3 kelime)
maximum_number_of_words = 5
```

### AMD Parametre Ayarlama Rehberi

**Problem: İnsanlar MACHINE olarak algılanıyor (false positive)**

| Parametre | Önceki | Yeni | Neden |
|-----------|--------|------|-------|
| `initial_silence` | 2500 | 3500 | İnsanlar bilinmeyen numaralara 2-3 sn sonra cevap verir |
| `greeting` | 1500 | 3000 | Türkçe/Almanca selamlamalar uzun olabilir |
| `maximum_number_of_words` | 3 | 5 | "Alo buyurun kimsiniz?" 3 kelimeyi aşar |

**Problem: Voicemail HUMAN olarak algılanıyor (false negative)**

| Parametre | Ayar | Neden |
|-----------|------|-------|
| `greeting` | Azalt (2000) | Daha kısa greeting'den sonra MACHINE kararı |
| `maximum_number_of_words` | Azalt (3-4) | Daha az kelimede MACHINE kararı |
| `total_analysis_time` | Azalt (2500) | Daha hızlı karar, ama NOTSURE riski artar |

**Altın Kural:** İlk başta `initial_silence = 3500` ve `maximum_number_of_words = 5` ile başla. Test et. Yanlış MACHINE tespiti fazlaysa `initial_silence` arttır. Yanlış HUMAN tespiti fazlaysa `maximum_number_of_words` azalt.

---

## A6. Adım 5: Backend Entegrasyonu

### Gereken Backend Bileşenleri

Yeni projede aşağıdaki backend dosyalarını oluştur/kopyala:

| # | Dosya | İçerik | Kopyalama Notu |
|---|-------|--------|----------------|
| 1 | `webhooks.py` | AMD result + Ultravox + call-failed webhook'ları | Mapping tablolarını kopyala |
| 2 | `outbound_calls.py` | `_monitor_ultravox_call()`, `_mark_call_failed()` | Monitor + SIP mapping |
| 3 | `ultravox_provider.py` | Ultravox API entegrasyonu + SIP routing | SIP credentials kısmı |
| 4 | `openai_provider.py` | ARI çağrı başlatma | ARI endpoint konfigürasyonu |
| 5 | `calls.py` | Hangup handler + `_cancel_ultravox_via_ari()` | İptal mekanizması |

### Minimum Webhook Handler (Kopyala-Yapıştır)

```python
# AMD Result Webhook — Asterisk'ten gelir
@router.post("/webhooks/amd-result")
async def amd_result_webhook(payload: AMDResultRequest, db: AsyncSession):
    """
    Asterisk AMD analiz sonucunu alır.
    - OpenAI çağrıları: uuid ile lookup
    - Ultravox çağrıları: phone (to_number) ile lookup
    """
    # UYARI: CallLog.phone_number BİR RELATIONSHIP'tir!
    # String karşılaştırma için CallLog.to_number kullan!
    
    if payload.uuid:
        call_log = await db.execute(
            select(CallLog).where(CallLog.call_sid == payload.uuid)
        )
    elif payload.phone:
        call_log = await db.execute(
            select(CallLog)
            .where(CallLog.to_number == payload.phone)
            .where(CallLog.provider == "ultravox")
            .where(CallLog.status.in_([
                CallStatus.QUEUED,
                CallStatus.RINGING, 
                CallStatus.CONNECTED,
                CallStatus.TALKING
            ]))
            .order_by(CallLog.created_at.desc())
        )
    
    if payload.status in ("MACHINE", "NOTSURE"):
        call_log.amd_status = payload.status
        call_log.amd_cause = payload.cause
        call_log.status = CallStatus.COMPLETED
        call_log.outcome = CallOutcome.VOICEMAIL
        call_log.hangup_cause = f"AMD:{payload.cause}"
```

### Kritik: Ultravox Webhook'ta AMD Koruma

Ultravox webhook handler'ında (call.ended event), en son aşamada şu korumayı ekle:

```python
# AMD sonucu Ultravox webhook'undan ÖNCE gelmiş olabilir
# AMD sonucunu korumak için override yap
if call_log.amd_status in ("MACHINE", "NOTSURE"):
    call_log.status = CallStatus.COMPLETED
    call_log.outcome = CallOutcome.VOICEMAIL
    # Diğer alanları Ultravox değiştirmiş olabilir, override et
```

Bu olmadan Ultravox webhook'u AMD'nin set ettiği VOICEMAIL outcome'unu SUCCESS ile ezer!

### SIP Code → Status/Outcome Mapping (Kopyala-Yapıştır)

```python
# SIP kodu geldiğinde CallLog'a nasıl yansıtılacağı
def _mark_call_failed(call_log, sip_code, hangup_cause):
    sip_map = {
        404: ("failed", CallStatus.FAILED, CallOutcome.FAILED),
        480: ("no-answer", CallStatus.NO_ANSWER, CallOutcome.NO_ANSWER),
        486: ("busy", CallStatus.BUSY, CallOutcome.BUSY),
        487: ("failed", CallStatus.FAILED, CallOutcome.FAILED),
        503: ("failed", CallStatus.FAILED, CallOutcome.FAILED),
        603: ("busy", CallStatus.BUSY, CallOutcome.BUSY),
    }
    category, status, outcome = sip_map.get(
        sip_code, ("failed", CallStatus.FAILED, CallOutcome.FAILED)
    )
    call_log.sip_code = sip_code
    call_log.hangup_cause = hangup_cause
    call_log.status = status
    call_log.outcome = outcome
```

---

## A7. Adım 6: Environment Variables

### Backend .env Dosyası (SIP ile İlgili Değişkenler)

```env
# --- SIP Trunk (VoIP sağlayıcı bilgileri) ---
SIP_TRUNK_HOST=85.95.239.198            # SIP sağlayıcı IP/hostname
SIP_TRUNK_PORT=5060                      # SIP port (genelde 5060)
SIP_TRUNK_USERNAME=101                   # SIP hesap kullanıcı adı
SIP_TRUNK_PASSWORD=gizli_sifre           # SIP hesap şifresi
SIP_TRUNK_CALLER_ID=491632086421         # Arayan numara (CallerID)

# --- Asterisk ARI (Backend → Asterisk iletişimi) ---
ASTERISK_HOST=asterisk                   # Docker container adı (network içi)
ASTERISK_ARI_PORT=8088                   # ARI HTTP port
ASTERISK_ARI_USER=voiceai                # ari.conf'taki kullanıcı adı
ASTERISK_ARI_PASSWORD=gizli_ari_sifresi  # ari.conf'taki şifre

# --- Asterisk SIP Bridge (Ultravox → Asterisk) ---
ASTERISK_EXTERNAL_HOST=37.27.119.79      # Sunucu PUBLIC IP (NAT arkasıysa!)
ASTERISK_SIP_PORT=5043                   # Asterisk SIP port
ULTRAVOX_SIP_USERNAME=ultravox           # pjsip.conf'taki username
ULTRAVOX_SIP_PASSWORD=gizli_sip_sifresi  # pjsip.conf'taki password

# --- AI Provider API Keys ---
ULTRAVOX_API_KEY=uv_xxx_yyy              # Ultravox API key
ULTRAVOX_WEBHOOK_URL=https://domain.com/api/v1/webhooks/ultravox
OPENAI_API_KEY=sk-xxx                    # OpenAI API key
```

### Hangi Şifre Nerede Eşleşmeli?

```
ULTRAVOX_SIP_PASSWORD  ←→  pjsip.conf [ultravox-auth] password
SIP_TRUNK_PASSWORD     ←→  pjsip.conf [trunk-auth] password
ASTERISK_ARI_USER      ←→  ari.conf kullanıcı adı
ASTERISK_ARI_PASSWORD  ←→  ari.conf şifre
EXTERNAL_IP            ←→  pjsip.conf external_signaling_address
```

> **DİKKAT:** Docker entrypoint script'i `__EXTERNAL_IP__`, `__SIP_TRUNK_PASSWORD__`, `__ULTRAVOX_SIP_PASSWORD__` placeholder'larını runtime'da environment variable'larla değiştirir. Dockerfile'da sed komutu var.

---

## A8. Adım 7: Test & Doğrulama

### Test 1: Asterisk Bağlantı Kontrolü

```bash
# SIP trunk kaydını kontrol et
docker exec voiceai-asterisk asterisk -rx "pjsip show registrations"
# Beklenen: trunk-reg → Registered

# Ultravox endpoint görünüyor mu?
docker exec voiceai-asterisk asterisk -rx "pjsip show endpoints"
# Beklenen: ultravox, trunk, voiceai endpoint'leri listelenir

# AMD modülü yüklü mü?
docker exec voiceai-asterisk asterisk -rx "module show like app_amd"
# Beklenen: app_amd.so → Running
```

### Test 2: Ultravox SIP Bağlantısı

1. Ultravox dashboard'dan bir test çağrısı başlat
2. Asterisk CLI'da izle:
```bash
docker exec -it voiceai-asterisk asterisk -rvvvv
# Gözle: 
# -- [from-ultravox] Ultravox bridge call to +49...
# -- PJSIP/trunk-xxx is ringing
```

### Test 3: AMD Testi

```bash
# Telesekreterli bir numarayı ara (test numarası kullan)
# Asterisk CLI'da gözle:
# AMD Result: MACHINE - MAXWORDS-6-5
# veya
# AMD Result: HUMAN - HUMAN-1-3500

# Backend loglarında kontrol et:
docker logs voiceai-backend --tail 50 | grep -i amd
# Beklenen: "AMD result received: MACHINE for +49..."
```

### Test 4: SIP Hata Kodları

| Test | Nasıl | Beklenti |
|------|-------|----------|
| Geçersiz numara | `+4900000000000` ara | sip_code=404, status=FAILED |
| Meşgul hat | Meşgul bir numara ara | sip_code=486, status=BUSY |
| Cevapsız | Bir numara çalsın ama cevaplama | sip_code=480, status=NO_ANSWER |
| Manuel iptal | Çalarken "Kapat" tıkla | sip_code=487, hangup_cause="User Hangup (Manual)" |
| Telesekreter | Voicemail'li numara ara | outcome=VOICEMAIL, amd_status=MACHINE |

### Test 5: Tam Döngü (End-to-End)

1. Frontend'ten bir Ultravox agent ile arama başlat
2. Telefon çalsın → Cevapla → AI konuşsun → Kapat
3. Çağrı loglarında kontrol et:
   - `status = completed`
   - `outcome = success`
   - `sip_code = 200`
   - `connected_at` ve `ended_at` dolu

---

## A9. Troubleshooting — Sık Karşılaşılan Hatalar

### Hata 1: "No path to translate from PJSIP/ultravox to PJSIP/trunk"

**Neden:** Ultravox opus codec gönderdi ama Asterisk opus transcode edemez.

**Çözüm:**
```ini
; pjsip.conf [ultravox] endpoint:
disallow=all
allow=g722    ; Yüksek kalite (16kHz)
allow=ulaw    ; Standart (8kHz)
allow=alaw    ; Alternatif (8kHz)
; OPUS EKLEME!
```

### Hata 2: "Endpoint not found for INVITE"

**Neden:** Asterisk, gelen SIP INVITE'ı tanımıyor.

**Çözüm:**
```ini
; pjsip.conf [global]:
endpoint_identifier_order=ip,username
; username ekle → Ultravox'un From header'ındaki username'den tanır
```

### Hata 3: AMD sonucu backend'e ulaşmıyor

**Neden:** `curl` komutu container network'ünde `backend` hostname'ini çözemez.

**Çözüm:**
- Docker Compose'da `asterisk` ve `backend` aynı network'te olmalı
- `curl http://backend:8000/...` şeklinde container adı kullan
- Docker network'ü kontrol: `docker network inspect voiceai_voiceai-network`

### Hata 4: `AttributeError: INITIATED` veya `IN_PROGRESS`

**Neden:** CallStatus enum'ında bu değerler yok.

**Çözüm:** Gerçek enum değerlerini kullan:
```python
# YANLIŞ:
CallStatus.INITIATED      # YOK!
CallStatus.IN_PROGRESS    # YOK!

# DOĞRU:
CallStatus.QUEUED         # Sırada
CallStatus.RINGING        # Çalıyor
CallStatus.CONNECTED      # Bağlandı
CallStatus.TALKING         # Konuşuyor
```

### Hata 5: `ArgumentError: Mapped instance expected for relationship comparison`

**Neden:** SQLAlchemy'de relationship alanıyla string karşılaştırma yapıyorsun.

**Çözüm:**
```python
# YANLIŞ:
CallLog.phone_number == "+49155..."  # phone_number bir RELATIONSHIP!

# DOĞRU:
CallLog.to_number == "+49155..."     # to_number gerçek string kolon
```

### Hata 6: Ultravox çağrısı "declined" oluyor ama aslında voicemail

**Neden:** AMD webhook geldi → VOICEMAIL set etti → Ultravox webhook geldi → SUCCESS/FAILED ile ezdi.

**Çözüm:** Ultravox webhook handler'ında en son aşamada AMD koruma ekle (bkz. A6 Backend Entegrasyonu).

### Hata 7: Çalan Ultravox çağrısı iptal edilemiyor

**Neden:** Ultravox `hang_up` API, henüz "joined" olmayan çağrılarda 422 verir.

**Çözüm:** Fallback olarak ARI üzerinden Asterisk kanalını DELETE et:
```python
# ARI'den kanalları listele → from-ultravox context'te eşleşeni bul → DELETE
channels = await ari_get("/ari/channels")
for ch in channels:
    if ch.get("dialplan", {}).get("context") == "from-ultravox":
        await ari_delete(f"/ari/channels/{ch['id']}")
```

### Hata 8: Tek yönlü ses (bir taraf duymuyor)

**Neden:** NAT sorunu. `external_signaling_address` yanlış.

**Çözüm:**
```ini
; pjsip.conf transport:
external_signaling_address=SUNUCUNUN_PUBLIC_IP
external_media_address=SUNUCUNUN_PUBLIC_IP

; endpoint'lerde:
rtp_symmetric=yes
force_rport=yes
direct_media=no
```

### Hata 9: SIP trunk register olamıyor

**Neden:** Firewall veya şifre hatası.

**Çözüm:**
```bash
# Firewall kontrol
ufw allow 5043/udp
ufw allow 5043/tcp
ufw allow 10000:10100/udp

# Registration durumunu izle
docker exec voiceai-asterisk asterisk -rx "pjsip show registrations"

# Debug loglama aç
docker exec voiceai-asterisk asterisk -rx "pjsip set logger on"
```

---

## A10. Öğrenilen Dersler (Lessons Learned)

### 1. Prompt-Based AMD Çalışmaz

Ultravox'un kendi AI'ına "Bu bir telesekreter mi?" diye sorma yaklaşımı **güvenilir değildir**. Üç farklı prompt denendi, üçü de başarısız oldu. STT transkripti voicemail mesajını yazıyor ama LLM yorumlayamıyor.

**Sonuç:** Her zaman Asterisk sinyal tabanlı AMD kullan. Dil bağımsız, güvenilir, hızlı.

### 2. AMD Çalışma Noktası Önemli

- **OpenAI/xAI/Gemini:** `Answer()` sonrası, `AudioSocket` öncesi
- **Ultravox:** `Dial() U()` subroutine içinde — cevaptan sonra, bridge'den önce

Bu fark kritik: Ultravox'ta `Answer()` ayrıca yapılmaz, `Dial()` otomatik cevaplar. AMD'yi U() subroutine ile araya sokmak gerekir.

### 3. Codec Negotiation Kuralları

```
Ultravox API → opus gönderir → Asterisk opus transcode EDEMEZ → HATA!
Çözüm: Ultravox endpoint'te opus KAPAT → g722'ye fallback yapar
g722 (16kHz) → ulaw/alaw (8kHz) transcode → Asterisk halledebilir ✓
```

### 4. Race Condition: AMD vs Ultravox Webhook

AMD webhook genellikle Ultravox webhook'undan ÖNCE gelir (AMD çok hızlı, Ultravox webhook asenkron). Ama sıra garantisi yok. Bu yüzden:
- AMD webhook → VOICEMAIL set eder
- Ultravox webhook → en son aşamada `amd_status` kontrol eder ve ezmiyor

### 5. Çağrı İptali Zinciri

```
Ultravox hang_up API (422 riski)
    → Fallback: ARI kanalı DELETE (Asterisk SIP CANCEL gönderir)
        → Ultravox bu CANCEL'ı alır → endReason=hangup
```

### 6. CallLog ile İlgili "Gotcha"lar

- `CallLog.phone_number` → **RELATIONSHIP** (PhoneNumber objesine FK, string DEĞİL)
- `CallLog.to_number` → **STRING KOLON** (telefon numarası, bunu kullan)
- `CallStatus.INITIATED`, `IN_PROGRESS` → **MEVCUT DEĞİL** → `QUEUED`, `TALKING` kullan
- `sip_code` nullable → bazı çağrılarda NULL olabilir

### 7. Docker Networking

Asterisk'in backend'e webhook göndermesi için:
- İkisi aynı Docker network'te olmalı
- `http://backend:8000/...` şeklinde container adı kullan
- `localhost` veya `127.0.0.1` ÇALIŞMAZ (ayrı container'lar)

### 8. pjsip.conf Template Sistemi

Docker entrypoint script'i şu placeholder'ları değiştirir:
```
__EXTERNAL_IP__          → $EXTERNAL_IP env var
__SIP_TRUNK_PASSWORD__   → $SIP_TRUNK_PASSWORD env var
__ULTRAVOX_SIP_PASSWORD__→ $ULTRAVOX_SIP_PASSWORD env var
```
pjsip.conf'a gerçek şifre YAZMA, placeholder bırak.

---

# BÖLÜM B — TEKNİK REFERANS (MEVCUT SİSTEM)

---

## 1. Genel Mimari

VoiceAI platformu iki farklı SIP çağrı yolu kullanır:

### Ultravox Çağrı Yolu
```
Ultravox AI Cloud
      │
      ▼ SIP INVITE
Asterisk PBX [from-ultravox]
      │
      ├─ Dial() U() → AMD analizi
      │     ├─ MACHINE/NOTSURE → webhook → ABORT
      │     └─ HUMAN → bridge devam
      │
      ▼ PJSIP
SIP Trunk (85.95.239.198)
      │
      ▼
Telefon
```

### OpenAI / xAI / Gemini Çağrı Yolu
```
Backend
      │
      ▼ ARI originate
Asterisk PBX [ai-outbound]
      │
      ▼ PJSIP
SIP Trunk (85.95.239.198)
      │
      ▼
Telefon cevaplar
      │
      ▼
AMD() analizi
      ├─ MACHINE/NOTSURE → webhook → Hangup
      └─ HUMAN → AudioSocket bridge → AI WebSocket
```

### Temel Fark
| Özellik | Ultravox | OpenAI/xAI/Gemini |
|---------|----------|-------------------|
| SIP başlatan | Ultravox Cloud | Asterisk (ARI) |
| AMD konumu | Dial() U() subroutine (cevaptan sonra, bridge'den önce) | Answer() sonrası, AudioSocket'ten önce |
| Audio bridge | Ultravox doğrudan SIP üzerinden konuşur | AudioSocket → WebSocket → AI |
| SIP code kaynağı | Ultravox API `sipDetails.terminationReason` | ARI channel monitor + Asterisk webhook |
| Çağrı izleme | `_monitor_ultravox_call()` + Ultravox webhook | `_monitor_outbound_channel()` + ARI |

---

## 2. CallLog Modeli — SIP Alanları

**Dosya:** `backend/app/models/models.py`

CallLog tablosunda SIP hata yönetimi için kullanılan 4 kritik alan:

| Alan | Tip | Açıklama |
|------|-----|----------|
| `sip_code` | `Integer` (nullable) | SIP response kodu (200, 404, 480, 486, 487, 503, 603) |
| `hangup_cause` | `String(100)` (nullable) | İnsan-okunabilir kapanma nedeni |
| `amd_status` | `String(20)` (nullable) | AMD sonucu: `HUMAN`, `MACHINE`, `NOTSURE` |
| `amd_cause` | `String(100)` (nullable) | AMD karar gerekçesi (örn: `MAXWORDS-6-5`, `TOOLONG-3500`) |

### CallStatus Enum (Çağrı Durumu)
```python
class CallStatus(str, enum.Enum):
    QUEUED       = "queued"        # Sırada bekliyor
    RINGING      = "ringing"       # Çalıyor
    CONNECTED    = "connected"     # Bağlandı
    TALKING      = "talking"       # Konuşuyor
    ON_HOLD      = "on_hold"       # Beklemede
    TRANSFERRED  = "transferred"   # Transfer edildi
    COMPLETED    = "completed"     # Tamamlandı
    FAILED       = "failed"        # Başarısız
    NO_ANSWER    = "no_answer"     # Cevapsız
    BUSY         = "busy"          # Meşgul
```

### CallOutcome Enum (Çağrı Sonucu)
```python
class CallOutcome(str, enum.Enum):
    SUCCESS             = "success"             # Başarılı konuşma
    VOICEMAIL           = "voicemail"           # Telesekreter / sesli mesaj
    NO_ANSWER           = "no_answer"           # Cevap vermedi
    BUSY                = "busy"                # Hat meşgul
    FAILED              = "failed"              # Teknik hata
    TRANSFERRED         = "transferred"         # Transfer edildi
    CALLBACK_SCHEDULED  = "callback_scheduled"  # Geri arama planlandı
```

---

## 3. SIP Code Mapping Tabloları

Sistemde 5 farklı SIP code mapping tablosu tanımlıdır. Her biri farklı bir durumda kullanılır.

### 3a. ULTRAVOX_TERMINATION_TO_SIP

**Dosyalar:** `backend/app/api/v1/webhooks.py` ve `backend/app/api/outbound_calls.py` (ikisi aynı)

Ultravox API'den gelen `sipDetails.terminationReason` değerini standart SIP koduna çevirir:

| Ultravox terminationReason | SIP Code | Açıklama |
|---------------------------|----------|----------|
| `SIP_TERMINATION_NORMAL` | 200 | Normal kapanma |
| `SIP_TERMINATION_INVALID_NUMBER` | 404 | Geçersiz numara |
| `SIP_TERMINATION_TIMEOUT` | 480 | Zaman aşımı (cevapsız) |
| `SIP_TERMINATION_DESTINATION_UNAVAILABLE` | 503 | Hedef ulaşılamaz |
| `SIP_TERMINATION_BUSY` | 486 | Hat meşgul |
| `SIP_TERMINATION_CANCELED` | 487 | Çağrı iptal edildi |
| `SIP_TERMINATION_REJECTED` | 603 | Çağrı reddedildi |
| `SIP_TERMINATION_UNKNOWN` | 0 | Bilinmeyen |

### 3b. ULTRAVOX_END_REASON_MAP

**Dosya:** `backend/app/api/v1/webhooks.py`

Ultravox `endReason` değerini CallStatus ve CallOutcome'a çevirir:

| endReason | CallStatus | CallOutcome |
|-----------|------------|-------------|
| `hangup` | COMPLETED | SUCCESS |
| `agent_hangup` | COMPLETED | SUCCESS |
| `timeout` | COMPLETED | NO_ANSWER |
| `unjoined` | FAILED | NO_ANSWER |
| `connection_error` | FAILED | FAILED |
| `system_error` | FAILED | FAILED |

### 3c. DIALSTATUS_TO_SIP

**Dosya:** `backend/app/api/v1/webhooks.py`

Asterisk `DIALSTATUS` değerini SIP koduna çevirir (OpenAI/xAI/Gemini provider):

| DIALSTATUS | SIP Code | Açıklama |
|------------|----------|----------|
| `BUSY` | 486 | Hat meşgul |
| `NOANSWER` | 480 | Cevapsız |
| `CONGESTION` | 503 | Network tıkanıklığı |
| `CHANUNAVAIL` | 503 | Kanal kullanılamaz |
| `CANCEL` | 487 | İptal edildi |

### 3d. ULTRAVOX_FAILURE_TERMINATIONS

**Dosya:** `backend/app/api/outbound_calls.py`

Ultravox monitor'un "başarısız" olarak değerlendirdiği termination reason'lar:

```
SIP_TERMINATION_INVALID_NUMBER
SIP_TERMINATION_TIMEOUT
SIP_TERMINATION_DESTINATION_UNAVAILABLE
SIP_TERMINATION_BUSY
SIP_TERMINATION_CANCELED
SIP_TERMINATION_REJECTED
```

> **Not:** `SIP_TERMINATION_NORMAL` ve `SIP_TERMINATION_UNKNOWN` bu sette YOK — yani bunlar "başarısız" sayılmaz.

### 3e. _mark_call_failed İç Mapping

**Dosya:** `backend/app/api/outbound_calls.py`

SIP kodunu CallStatus/CallOutcome'a çevirir (hem Ultravox hem OpenAI monitor tarafından kullanılır):

| SIP Code | Durum Kategorisi | CallStatus | CallOutcome |
|----------|-----------------|------------|-------------|
| 404 | failed | FAILED | FAILED |
| 480 | no-answer | NO_ANSWER | NO_ANSWER |
| 486 | busy | BUSY | BUSY |
| 487 | failed | FAILED | FAILED |
| 503 | failed | FAILED | FAILED |
| 603 | busy | BUSY | BUSY |
| (diğer) | failed | FAILED | FAILED |

---

## 4. Ultravox Provider — SIP Hata Yönetimi

### 4.1. SIP Bağlantı Konfigürasyonu

**Dosya:** `backend/app/services/ultravox_provider.py`

Ultravox, Asterisk üzerinden SIP çağrısı yapar:

```
Ultravox AI Cloud → SIP INVITE → Asterisk (37.27.119.79:5043) → SIP Trunk → Telefon
```

**Konfigürasyon değerleri:**
| Parametre | Değer | Açıklama |
|-----------|-------|----------|
| `sip_trunk_host` | `ASTERISK_EXTERNAL_HOST` (37.27.119.79) | Asterisk sunucu IP'si |
| `sip_trunk_port` | `ASTERISK_SIP_PORT` (5043) | Asterisk SIP port |
| `sip_username` | `ULTRAVOX_SIP_USERNAME` (ultravox) | PJSIP auth username |
| `sip_password` | `ULTRAVOX_SIP_PASSWORD` | PJSIP auth password |

**PJSIP endpoint konfigürasyonu** (`asterisk/pjsip.conf`):
```ini
[ultravox]
type=endpoint
context=from-ultravox      # Gelen çağrılar bu dialplan'a gider
allow=g722                 # Yüksek kalite codec
allow=ulaw                 # Standart codec
allow=alaw                 # Alternatif codec
# NOT: opus kaldırıldı — Asterisk'te opus transcoder yok
```

> **ÖNEMLİ:** `opus` codec'i kaldırılmıştır. Ultravox opus gönderirse ve Asterisk'in opus transcoder'ı yoksa, "No path to translate from PJSIP/ultravox to PJSIP/trunk" hatası oluşur. Bu sorun `g722/ulaw/alaw` ile çözüldü.

### 4.2. SIP Hata Algılama — 3 Katmanlı Sistem

Ultravox çağrıları için SIP hata kodları **3 farklı mekanizma** ile algılanır:

#### Katman 1: Ultravox Call Monitor (Background Polling)

**Dosya:** `backend/app/api/outbound_calls.py` — `_monitor_ultravox_call()`

- Çağrı başlatıldıktan 5 saniye sonra başlar
- Her 5 saniyede Ultravox API'yi poll eder (`GET /calls/{id}`)
- `endReason` ve `sipDetails.terminationReason` kontrol edilir
- Failure termination bulunursa → `_mark_call_failed()` çağrılır
- Çağrı aktifse (status: listening/thinking/speaking) → izleme durur
- 2 dakika timeout → SIP 480 (cevapsız)

**Akış:**
```
Poll → endReason var mı?
  ├─ Hayır, aktif → İzlemeyi durdur (çağrı başarılı bağlandı)
  ├─ Hayır, idle → Tekrar poll
  └─ Evet → terminationReason kontrol
       ├─ FAILURE_TERMINATIONS içinde → _mark_call_failed(sip_code)
       ├─ unjoined/connection_error/system_error → _mark_call_failed(503)
       └─ hangup/agent_hangup → Normal (webhook yönetir)
```

#### Katman 2: Ultravox Webhook

**Dosya:** `backend/app/api/v1/webhooks.py` — `/api/v1/webhooks/ultravox`

Ultravox `call.ended` webhook'u geldiğinde 4 adımlı SIP çözümleme yapılır:

1. **Ultravox API'den tam çağrı bilgisi çekilir** → `sipDetails.terminationReason` alınır
2. **`endReason` → ilk mapping** (temel Status/Outcome ataması)
3. **SIP termination → override** (daha kesin SIP bilgisiyle Status/Outcome güncellenir):

   | terminationReason | CallStatus | CallOutcome |
   |-------------------|------------|-------------|
   | `SIP_TERMINATION_INVALID_NUMBER` | FAILED | FAILED |
   | `SIP_TERMINATION_BUSY` | BUSY | BUSY |
   | `SIP_TERMINATION_TIMEOUT` | NO_ANSWER | NO_ANSWER |
   | `SIP_TERMINATION_DESTINATION_UNAVAILABLE` | FAILED | FAILED |
   | `SIP_TERMINATION_REJECTED` | FAILED | BUSY |
   | `SIP_TERMINATION_CANCELED` | FAILED | FAILED |

4. **AMD override** (en yüksek öncelik):
   ```
   Eğer call_log.amd_status == "MACHINE" veya "NOTSURE":
       → status = COMPLETED
       → outcome = VOICEMAIL
   ```

   > Bu koruma, AMD webhook'un Ultravox webhook'undan ÖNCE gelip CallLog'u güncellediği durumda, Ultravox webhook'unun AMD sonucunu ezmemesini sağlar.

#### Katman 3: Asterisk AMD Webhook

**Dosya:** `backend/app/api/v1/webhooks.py` — `/api/v1/webhooks/amd-result`

Asterisk, çağrı cevaplandıktan sonra AMD analizi yapar. Sonuç:
- `MACHINE` veya `NOTSURE` → CallLog: `COMPLETED / VOICEMAIL / AMD:{cause}`
- `HUMAN` → Hiçbir şey yapmaz (bridge devam eder)

**Ultravox için lookup:** Telefon numarasıyla (`CallLog.to_number`) aktif çağrı aranır.

### 4.3. Ultravox Çağrı İptali (Manuel Hangup)

**Dosya:** `backend/app/api/v1/calls.py`

Ultravox çağrısı 3 farklı durumda iptal edilebilir:

| Durum | Yöntem | SIP Code |
|-------|--------|----------|
| RINGING (çalıyor) | ARI channel DELETE → SIP CANCEL | 487 |
| CONNECTED (bağlı) | Ultravox `hang_up` API | 200 |
| hang_up 422 hatası | Fallback: ARI channel DELETE | 487 |

**`_cancel_ultravox_via_ari()` fonksiyonu:**
- ARI'den tüm kanalları listeler
- `from-ultravox` context'inde eşleşen kanalı bulur
- `DELETE /ari/channels/{id}` → Asterisk SIP CANCEL gönderir

---

## 5. OpenAI / xAI / Gemini Provider — SIP Hata Yönetimi

### 5.1. Çağrı Başlatma

**Dosya:** `backend/app/services/openai_provider.py`

Backend, ARI (Asterisk REST Interface) üzerinden çağrı başlatır:
```
POST /ari/channels
  endpoint: PJSIP/{phone}@trunk
  context: ai-outbound
  app: voiceai
  variables: { VOICEAI_UUID, VOICEAI_AGENT_ID }
```

### 5.2. SIP Hata Algılama — ARI Channel Monitor

**Dosya:** `backend/app/api/outbound_calls.py` — `_monitor_outbound_channel()`

- Her 3 saniyede ARI channel status kontrol edilir
- Channel 404 olduğunda (kanal artık yok):

| Durum | SIP Code | Mantık |
|-------|----------|--------|
| `saw_ringing=True` | 486 | Çaldı ama cevap vermedi → meşgul/reddetti |
| `poll_count <= 1` (< 6 sn) | 404 | Çok hızlı kapandı → geçersiz numara |
| Diğer | 480 | Genel erişilemezlik |

- Bridge aktif olduysa (`call_bridge_active:{uuid}` Redis key) → izleme durur
- 2 dakika timeout → SIP 480

### 5.3. Asterisk AMD (OpenAI/xAI/Gemini)

**Dosya:** `asterisk/extensions.conf` — `[ai-outbound]` context

```
exten => s,1,Answer()
  → AMD()
  → MACHINE/NOTSURE → [amd_machine] context
       → curl POST /webhooks/amd-result {"uuid":"${VOICEAI_UUID}", ...}
       → Hangup()
  → HUMAN → AudioSocket bridge → AI WebSocket
```

**AMD webhook lookup:** UUID ile (`CallLog.call_sid`) aranır.

### 5.4. Manuel Hangup (OpenAI/xAI/Gemini)

**Dosya:** `backend/app/services/openai_provider.py`

```
Redis hangup_signal:{call_id} → 1
  → Bridge cleanup
  → ARI DELETE call_channel:{call_id}
```

SIP kodları `calls.py` hangup handler tarafından atanır:
- RINGING → `sip_code = 487` (Request Terminated)
- Diğer → `sip_code = 200` (Normal Clearing)

---

## 6. Asterisk Dialplan — SIP ve AMD İşleme

### 6.1. [from-ultravox] Context

**Dosya:** `asterisk/extensions.conf`

Ultravox'tan gelen SIP çağrılarını karşılar ve trunk üzerinden yönlendirir:

```ini
[from-ultravox]
exten => _+X.,1,NoOp(Ultravox bridge call to ${EXTEN})
 same => n,Set(CALLERID(num)=${VOICEAI_CALLERID})
 same => n,Set(CALLERID(name)=VoiceAI)
 same => n,Set(_ULTRAVOX_PHONE=${EXTEN})
 same => n,Dial(PJSIP/${EXTEN:1}@${SIP_TRUNK},120,gU(ultravox-amd-check,s,1))
 same => n,Hangup()
```

**Dial() parametreleri:**
| Param | Değer | Açıklama |
|-------|-------|----------|
| `120` | Timeout | 120 saniye çalma süresi |
| `g` | Go on | Dial() sonrasında dialplan'a devam et |
| `U(ultravox-amd-check,s,1)` | Subroutine | Karşı taraf cevapladıktan SONRA, bridge kurulmadan ÖNCE çalışır |

**`_ULTRAVOX_PHONE` değişkeni:**
- `_` prefix'i = channel variable (child channel'a miras geçer)
- AMD subroutine'de telefon numarasını backend'e iletmek için kullanılır
- `+X.` pattern → `${EXTEN}` doğrudan (örn: `+4915510528458`)
- `00X.` pattern → `+${EXTEN:2}` (00 → + dönüşümü)
- `X.` pattern → `+${EXTEN}` (+ prefix eklenir)

### 6.2. [ultravox-amd-check] Subroutine

**Dosya:** `asterisk/extensions.conf`

Dial() U() option ile çağrılan subroutine. Karşı taraf cevapladıktan sonra çalışır:

```ini
[ultravox-amd-check]
exten => s,1,NoOp(Ultravox AMD check for ${ULTRAVOX_PHONE})
 same => n,AMD()
 same => n,NoOp(Ultravox AMD Result: ${AMDSTATUS} - ${AMDCAUSE})
 same => n,GotoIf($["${AMDSTATUS}" = "MACHINE"]?machine)
 same => n,GotoIf($["${AMDSTATUS}" = "NOTSURE"]?machine)
 ; HUMAN detected - Return() → Dial() bridge'i kurar → Ultravox AI konuşur
 same => n,Return()
 same => n(machine),NoOp(Ultravox AMD: ${AMDSTATUS} for ${ULTRAVOX_PHONE})
 same => n,System(curl -s -X POST http://backend:8000/api/v1/webhooks/amd-result ...)
 same => n,Set(GOSUB_RESULT=ABORT)
 same => n,Return()
```

**Kritik detay — `GOSUB_RESULT=ABORT`:**
- `U()` subroutine'de `GOSUB_RESULT=ABORT` set edildiğinde, Dial() her iki kanalı da (caller + called) düşürür
- Bu, Ultravox tarafındaki SIP bağlantısını da sonlandırır
- Ultravox, `SIP_TERMINATION_CANCELED` alır ve `endReason = hangup` veya `agent_hangup` ile çağrıyı bitirir

### 6.3. [ai-outbound] Context

**Dosya:** `asterisk/extensions.conf`

OpenAI/xAI/Gemini aramaları için AMD ve AudioSocket bridge:

```ini
[ai-outbound]
exten => s,1,Answer()
 same => n,AMD()
 same => n,NoOp(AMD Result: ${AMDSTATUS} - ${AMDCAUSE})
 same => n,GotoIf($["${AMDSTATUS}" = "MACHINE"]?amd_machine,s,1)
 same => n,GotoIf($["${AMDSTATUS}" = "NOTSURE"]?amd_machine,s,1)
 ; HUMAN → AI agent'a bağla
 same => n,Dial(AudioSocket/${AUDIOSOCKET_ADDR}/${VOICEAI_UUID}/c(slin24))
 same => n,Hangup()
```

**Fark:** Burada AMD `Answer()` sonrasında çalışır (çünkü ARI originate zaten cevaplamıştır). Ultravox'ta ise AMD, `Dial() U()` ile cevaptan sonra ama bridge'den önce çalışır.

### 6.4. [amd_machine] Context

**Dosya:** `asterisk/extensions.conf`

AMD makine tespit ettiğinde:

```ini
[amd_machine]
exten => s,1,NoOp(AMD Machine Detected: UUID=${VOICEAI_UUID}, Status=${AMDSTATUS})
 same => n,System(curl -s -X POST http://backend:8000/api/v1/webhooks/amd-result
                  -H "Content-Type: application/json"
                  -d '{"uuid":"${VOICEAI_UUID}","status":"${AMDSTATUS}","cause":"${AMDCAUSE}"}' &)
 same => n,Hangup()
```

> **Not:** `&` ile curl arka planda çalışır — Hangup() beklemeden yapılır.

### 6.5. AMD Konfigürasyonu

**Dosya:** `asterisk/amd.conf`

| Parametre | Değer | Açıklama |
|-----------|-------|----------|
| `total_analysis_time` | 3500 ms | Toplam analiz süresi. Aşılırsa → `NOTSURE` |
| `silence_threshold` | 256 | Sessizlik eşiği (0–32767). Bu değerin altı = sessizlik |
| `initial_silence` | 3500 ms | Greeting öncesi max sessizlik süresi. Aşılırsa → `MACHINE` |
| `after_greeting_silence` | 500 ms | Greeting sonrası sessizlik. Aşılırsa → `HUMAN` (kişi konuşup sustu) |
| `greeting` | 3000 ms | Max greeting uzunluğu. Aşılırsa → `MACHINE` (uzun kayıtlı mesaj) |
| `min_word_length` | 100 ms | Kelime sayılması için min ses süresi |
| `maximum_word_length` | 5000 ms | Tek bir ifadenin max süresi |
| `between_words_silence` | 50 ms | Kelimeler arası sessizlik (kelime ayırıcı) |
| `maximum_number_of_words` | 5 | Max kelime sayısı. Aşılırsa → `MACHINE` |

**Optimizasyon notları:**
- `initial_silence = 3500`: Türk/Alman kullanıcılar bilinmeyen numaraya 2-3 saniye sonra "Alo?" diyebilir. Önceki 2500 değeri yanlış MACHINE tespitine neden oluyordu.
- `after_greeting_silence = 500`: "Alo" dedikten sonra 500ms sessizlik → HUMAN. Hızlı karar.
- `greeting = 3000`: Türkçe selamlamalar 2+ saniye sürebilir. Önceki 1500 değeri kısa kalıyordu.
- `maximum_number_of_words = 5`: Voicemail mesajları genellikle 6+ kelime. 5 kelimeye kadar HUMAN kabul edilir.

---

## 7. Backend Webhook Endpoint'leri

### 7.1. `/api/v1/webhooks/amd-result` (POST)

**Dosya:** `backend/app/api/v1/webhooks.py`

**Amaç:** Asterisk AMD sonucunu alır ve CallLog'u günceller.

**Request body:**
```json
{
    "uuid": "abc-123",       // OpenAI aramaları için (call_sid)
    "phone": "+4915510528458", // Ultravox aramaları için (to_number)
    "status": "MACHINE",     // MACHINE, HUMAN, NOTSURE
    "cause": "MAXWORDS-6-5", // AMD karar gerekçesi
    "source": "ultravox"     // Opsiyonel: "ultravox" ise phone lookup yapılır
}
```

**CallLog lookup mantığı:**
1. `uuid` varsa → `CallLog.call_sid == uuid`
2. `uuid` yoksa ve `phone` varsa → `CallLog.to_number == phone` + `provider == "ultravox"` + aktif statü
3. `+` prefix'siz de dener (numara formatı uyumsuzluğu durumunda)

**Aktif statüler:** `QUEUED, RINGING, CONNECTED, TALKING`

**MACHINE/NOTSURE sonucu:**
```python
call_log.amd_status   = "MACHINE"          # veya "NOTSURE"
call_log.amd_cause    = "MAXWORDS-6-5"     # AMD gerekçesi
call_log.status       = CallStatus.COMPLETED
call_log.outcome      = CallOutcome.VOICEMAIL
call_log.hangup_cause = "AMD:MAXWORDS-6-5"
call_log.ended_at     = datetime.utcnow()
```

### 7.2. `/api/v1/webhooks/call-failed` (POST)

**Dosya:** `backend/app/api/v1/webhooks.py`

**Amaç:** Asterisk'ten çağrı başarısız bildirimini alır (OpenAI/xAI/Gemini provider).

**Request body:**
```json
{
    "uuid": "abc-123",
    "status": "BUSY",    // BUSY, NOANSWER, CONGESTION, CHANUNAVAIL, CANCEL
    "cause": ""          // Asterisk HANGUPCAUSE
}
```

**İşlem:**
```python
sip_code, hangup_cause = DIALSTATUS_TO_SIP[payload.status]
call_log.sip_code     = sip_code
call_log.hangup_cause = hangup_cause
call_log.status       = CallStatus.NO_ANSWER
call_log.outcome      = CallOutcome.NO_ANSWER
```

### 7.3. `/api/v1/webhooks/ultravox` (POST)

**Dosya:** `backend/app/api/v1/webhooks.py`

**Amaç:** Ultravox'tan çağrı olaylarını alır.

**Olaylar:**
- `call.started` → `status = CONNECTED`, `connected_at = now()`
- `call.ended` / `call.billed` → 4 katmanlı SIP çözümleme (bkz. Bölüm 4.2)

**4 Katmanlı SIP Çözümleme Sırası:**

```
1. Ultravox API → sipDetails.terminationReason → sip_code + hangup_cause
2. endReason → ilk CallStatus + CallOutcome ataması
3. terminationReason → daha kesin Status/Outcome override
4. AMD koruma → amd_status MACHINE/NOTSURE ise → VOICEMAIL korunur
```

**Öncelik sırası (en düşükten en yükseğe):**
```
endReason mapping < SIP termination override < AMD override
```

---

## 8. Senaryo Bazlı Akış Diyagramları

### Senaryo 1: Müşteri Meşgul (BUSY)

**Ultravox:**
```
Ultravox → SIP → Asterisk → Trunk → 486 Busy
Ultravox API: sipDetails.terminationReason = SIP_TERMINATION_BUSY
  → Monitor: _mark_call_failed(sip_code=486)
  → Webhook: SIP override → BUSY / BUSY
  → Sonuç: sip_code=486, status=BUSY, outcome=BUSY
```

**OpenAI/xAI/Gemini:**
```
ARI originate → Trunk → 486 Busy
ARI channel sonlanır → monitor: saw_ringing=True
  → _mark_call_failed(sip_code=486)
  → Sonuç: sip_code=486, status=BUSY, outcome=BUSY
```

### Senaryo 2: Cevapsız (NO ANSWER)

**Ultravox:**
```
Ultravox → SIP → Asterisk → Trunk → Timeout (120s)
Ultravox API: sipDetails.terminationReason = SIP_TERMINATION_TIMEOUT
  → Monitor: _mark_call_failed(sip_code=480)
  → Webhook: SIP override → NO_ANSWER / NO_ANSWER
  → Sonuç: sip_code=480, status=NO_ANSWER, outcome=NO_ANSWER
```

**OpenAI/xAI/Gemini:**
```
ARI originate → Trunk → Çalıyor ama cevap yok
Monitor 2dk timeout → _mark_call_failed(sip_code=480)
  → Sonuç: sip_code=480, status=NO_ANSWER, outcome=NO_ANSWER
```

### Senaryo 3: Telesekreter / Sesli Mesaj (VOICEMAIL)

**Ultravox:**
```
Ultravox → SIP → Asterisk → Trunk → Cevap
Asterisk [from-ultravox] → Dial() U() → [ultravox-amd-check]
  → AMD() → MACHINE (cause: MAXWORDS-6-5)
  → curl POST /webhooks/amd-result {phone, status, cause, source}
  → GOSUB_RESULT=ABORT → Her iki kanal düşer
  → Backend: status=COMPLETED, outcome=VOICEMAIL, amd_status=MACHINE

(Sonra Ultravox webhook gelir)
  → AMD override aktif: amd_status=MACHINE → outcome=VOICEMAIL korunur
  → Sonuç: sip_code=487, status=COMPLETED, outcome=VOICEMAIL
```

**OpenAI/xAI/Gemini:**
```
ARI originate → Trunk → Cevap
Asterisk [ai-outbound] → Answer() → AMD()
  → MACHINE (cause: TOOLONG-3500)
  → [amd_machine] → curl POST /webhooks/amd-result {uuid, status, cause}
  → Hangup()
  → Backend: status=COMPLETED, outcome=VOICEMAIL, amd_status=MACHINE
  → Sonuç: status=COMPLETED, outcome=VOICEMAIL
```

### Senaryo 4: Geçersiz Numara (INVALID NUMBER)

**Ultravox:**
```
Ultravox → SIP → Asterisk → Trunk → 404 Not Found
Ultravox API: sipDetails.terminationReason = SIP_TERMINATION_INVALID_NUMBER
  → Monitor: _mark_call_failed(sip_code=404)
  → Sonuç: sip_code=404, status=FAILED, outcome=FAILED
```

**OpenAI/xAI/Gemini:**
```
ARI originate → Trunk → Hemen kapandı (<6s, ringing yok)
Monitor: poll_count <= 1 → _mark_call_failed(sip_code=404)
  → Sonuç: sip_code=404, status=FAILED, outcome=FAILED
```

### Senaryo 5: Kullanıcı Manuel İptal (Ringing)

**Ultravox:**
```
Kullanıcı "Çağrıyı Kapat" tıklar (RINGING durumunda)
  → Backend: end_call() → Ultravox hang_up API
  → 422 hatası (henüz bağlanmadı) → Fallback
  → _cancel_ultravox_via_ari()
       → ARI kanalları listele
       → from-ultravox context'inde eşleşen kanalı bul
       → DELETE /ari/channels/{id} → Asterisk SIP CANCEL gönderir
  → sip_code=487, hangup_cause="User Hangup (Manual)"
```

**OpenAI/xAI/Gemini:**
```
Kullanıcı "Çağrıyı Kapat" tıklar (RINGING durumunda)
  → Redis hangup_signal:{call_id} = 1
  → ARI DELETE call_channel:{call_id}
  → sip_code=487, hangup_cause="User Hangup (Manual)"
```

### Senaryo 6: Başarılı Çağrı ve Normal Kapanma

**Ultravox:**
```
Ultravox → SIP → Asterisk → Trunk → Cevap
AMD() → HUMAN → bridge kurulur → AI konuşur
Karşı taraf kapattığında:
  → Ultravox API: endReason=hangup, SIP_TERMINATION_NORMAL
  → Webhook: status=COMPLETED, outcome=SUCCESS, sip_code=200
```

**OpenAI/xAI/Gemini:**
```
ARI originate → Trunk → Cevap
AMD() → HUMAN → AudioSocket bridge → AI konuşur
Karşı taraf kapattığında:
  → Bridge sonlanır → DB güncelleme
  → status=COMPLETED, outcome=SUCCESS
```

### Senaryo 7: Hedef Ulaşılamaz (DESTINATION UNAVAILABLE)

**Ultravox:**
```
SIP_TERMINATION_DESTINATION_UNAVAILABLE → sip_code=503
  → status=FAILED, outcome=FAILED
```

**OpenAI/xAI/Gemini:**
```
CONGESTION/CHANUNAVAIL → sip_code=503
  → status=FAILED, outcome=FAILED
```

### Senaryo 8: Çağrı Reddedildi (REJECTED)

**Ultravox:**
```
SIP_TERMINATION_REJECTED → sip_code=603
  → status=FAILED, outcome=BUSY
```

**OpenAI/xAI/Gemini:**
```
Genellikle 486 BUSY olarak gelir (SIP trunk 603 göndermez)
  → sip_code=486, status=BUSY, outcome=BUSY
```

---

## 9. SIP Code Referans Tablosu

| SIP Code | RFC Adı | Platformdaki Anlamı | CallStatus | CallOutcome | Providerlar |
|----------|---------|---------------------|------------|-------------|-------------|
| **200** | OK | Normal kapanma, başarılı çağrı | COMPLETED | SUCCESS | Tümü |
| **404** | Not Found | Geçersiz veya mevcut olmayan numara | FAILED | FAILED | Tümü |
| **480** | Temporarily Unavailable | Cevapsız, zaman aşımı | NO_ANSWER | NO_ANSWER | Tümü |
| **486** | Busy Here | Hat meşgul | BUSY | BUSY | Tümü |
| **487** | Request Terminated | Çağrı iptal edildi (cancel) | FAILED | FAILED | Tümü |
| **503** | Service Unavailable | Hedef ulaşılamaz, network sorunu | FAILED | FAILED | Tümü |
| **603** | Decline | Çağrı reddedildi | BUSY* | BUSY | Ultravox |
| **0** | Unknown | Bilinmeyen SIP sonucu | — | — | Ultravox |

> **Not:** 603 Ultravox webhook'unda `FAILED/BUSY`, `_mark_call_failed`'da ise `BUSY/BUSY` olarak değerlendirilir.

---

## 10. Yapılan Geliştirmeler — Kronolojik

### 10.1. Ultravox SIP Hata Kodu Algılama (commit `fd54150`)

**Sorun:** Ultravox aramaları başarısız olduğunda (meşgul, cevapsız, geçersiz numara), CallLog'da SIP kodu ve hata nedeni kaydedilmiyordu. Tüm başarısız aramalar aynı generic "failed" durumda kalıyordu.

**Çözüm:**
- `ULTRAVOX_TERMINATION_TO_SIP` mapping tablosu oluşturuldu
- `ULTRAVOX_END_REASON_MAP` ile `endReason` → Status/Outcome mapping eklendi
- Ultravox webhook'una 3 katmanlı SIP çözümleme eklendi (endReason → SIP termination → override)
- `sipDetails.terminationReason` Ultravox API'den çekilip `sip_code` ve `hangup_cause` olarak kaydedildi

**Etkilenen dosyalar:**
- `backend/app/api/v1/webhooks.py`

### 10.2. Ultravox Çağrı Monitor — Meşgul/Cevapsız Tespiti (commit `af8fb33`)

**Sorun:** Ultravox webhook bazen gecikiyordu veya hiç gelmiyordu. Bu durumda başarısız aramalar tespit edilemiyordu.

**Çözüm:**
- `_monitor_ultravox_call()` background polling fonksiyonu eklendi
- Her 5 saniyede Ultravox API poll edilerek `endReason` + `sipDetails` kontrol edilir
- Failure termination tespitinde `_mark_call_failed()` çağrılır → SIP kodu ve hangup cause kaydedilir
- Çağrı aktif olduğunda (listening/thinking/speaking) izleme durur
- 2 dakika timeout → SIP 480 (cevapsız)

**Etkilenen dosyalar:**
- `backend/app/api/outbound_calls.py`

### 10.3. Ultravox Çalıyor Durumunda İptal (commit `2e04a1f`)

**Sorun:** Ultravox API'nin `hang_up` endpoint'i, çağrı henüz "joined" olmadığında (çalıyor durumu) 422 hatası veriyordu. `DELETE` endpoint'i de 425 veriyordu. Yani çalan bir Ultravox çağrısını iptal etmenin yolu yoktu.

**Çözüm:**
- Hangup handler'a fallback mekanizması eklendi:
  1. Önce `hang_up` API dene
  2. 422 hatası → `_cancel_ultravox_via_ari()` çağır
- `_cancel_ultravox_via_ari()` fonksiyonu: ARI kanallarını listeleyip `from-ultravox` context'indeki eşleşen kanalı DELETE eder → Asterisk SIP CANCEL gönderir

**Etkilenen dosyalar:**
- `backend/app/api/v1/calls.py`

### 10.4. Ultravox SIP Routing: Asterisk Üzerinden (commit `1e1bb36`)

**Sorun:** Ultravox doğrudan SIP trunk'a bağlanıyordu. Bu durumda:
- Çalan çağrıları iptal etmek mümkün değildi (Ultravox API 422/425)
- AMD analizi yapılamıyordu (Asterisk devre dışıydı)
- SIP CANCEL göndermek için Asterisk gerekiyordu

**Çözüm:**
- Ultravox SIP routing: doğrudan trunk yerine Asterisk üzerinden geçirildi
- `ultravox_provider.py`: SIP hedef `SIP_TRUNK_HOST:5060` → `ASTERISK_EXTERNAL_HOST:5043`
- Asterisk `[ultravox]` endpoint yapılandırıldı (PJSIP auth, codec ayarları)
- `[from-ultravox]` dialplan context'i oluşturuldu

**Etkilenen dosyalar:**
- `backend/app/services/ultravox_provider.py`
- `asterisk/pjsip.conf`
- `asterisk/extensions.conf`

### 10.5. Opus Codec Fix (commit `9fb189f`)

**Sorun:** Ultravox `opus` codec'i gönderiyordu. Asterisk'te opus transcoder olmadığı için trunk'a (ulaw/alaw) çeviremiyordu: "No path to translate from PJSIP/ultravox to PJSIP/trunk" hatası.

**Çözüm:**
- `[ultravox]` endpoint'ten `allow=opus` kaldırıldı
- `allow=g722, allow=ulaw, allow=alaw` bırakıldı
- Ultravox, codec negotiation'da g722'ye fallback yapıyor

**Etkilenen dosyalar:**
- `asterisk/pjsip.conf`

### 10.6. Ultravox İçin Asterisk AMD (commit `d9be6b2`)

**Sorun:** Ultravox'un kendi AI'ı (prompt tabanlı AMD) telesekreteri güvenilir şekilde algılayamıyordu. 3 test çağrısının 3'ünde de başarısız oldu. STT transkripti voicemail mesajını yazıyor ama LLM bunu "telesekreter" olarak yorumlayamıyordu.

**Çözüm:**
- `[from-ultravox]` context'ine `Dial() U(ultravox-amd-check,s,1)` eklendi
- `[ultravox-amd-check]` subroutine oluşturuldu:
  - Karşı taraf cevapladıktan SONRA, Ultravox bridge'inden ÖNCE çalışır
  - `AMD()` çalıştırır → sinyal tabanlı analiz (dil bağımsız)
  - MACHINE/NOTSURE → backend webhook + `GOSUB_RESULT=ABORT` (her iki kanal düşer)
  - HUMAN → bridge devam, Ultravox AI konuşur
- AMD webhook'a phone-number lookup eklendi (Ultravox UUID bilmez)
- Ultravox webhook'a AMD koruma eklendi (AMD sonucu korunur, Ultravox webhook ezmez)

**Etkilenen dosyalar:**
- `asterisk/extensions.conf`
- `backend/app/api/v1/webhooks.py`

### 10.7. AMD Webhook Bug Fix — Enum Hatası (commit `67cddce`)

**Sorun:** AMD webhook'ta `CallStatus.INITIATED` ve `CallStatus.IN_PROGRESS` kullanılmış ama bu enum değerleri mevcut değildi → `AttributeError: INITIATED` → 500 hatası → AMD sonucu kaydedilemiyordu.

**Çözüm:**
- `CallStatus.INITIATED` → `CallStatus.QUEUED`
- `CallStatus.IN_PROGRESS` → `CallStatus.TALKING`

**Etkilenen dosyalar:**
- `backend/app/api/v1/webhooks.py`

### 10.8. AMD Webhook Bug Fix — Relationship Hatası (commit `d511226`)

**Sorun:** `CallLog.phone_number` bir `relationship` (PhoneNumber ORM objesine FK), string kolon değil. String karşılaştırma yapıldığında: `ArgumentError: Mapped instance expected for relationship comparison` → 500 hatası.

**Çözüm:**
- `CallLog.phone_number` → `CallLog.to_number` (gerçek string kolon)

**Etkilenen dosyalar:**
- `backend/app/api/v1/webhooks.py`

---

## 11. Dosya Referansları

| Dosya | Satır | İçerik |
|-------|-------|--------|
| `backend/app/models/models.py` | 34-52 | CallStatus ve CallOutcome enum'ları |
| `backend/app/models/models.py` | 448 | `to_number` kolonu |
| `backend/app/models/models.py` | 472-480 | `sip_code`, `hangup_cause`, `amd_status`, `amd_cause` alanları |
| `backend/app/api/v1/webhooks.py` | 338-413 | AMD result webhook |
| `backend/app/api/v1/webhooks.py` | 427-474 | Call failed webhook + DIALSTATUS_TO_SIP |
| `backend/app/api/v1/webhooks.py` | 496-504 | ULTRAVOX_TERMINATION_TO_SIP mapping |
| `backend/app/api/v1/webhooks.py` | 506-513 | ULTRAVOX_END_REASON_MAP |
| `backend/app/api/v1/webhooks.py` | 515-652 | Ultravox webhook handler (4 katmanlı SIP çözümleme) |
| `backend/app/api/outbound_calls.py` | 183-210 | `_mark_call_failed()` fonksiyonu |
| `backend/app/api/outbound_calls.py` | 237-254 | ULTRAVOX_TERMINATION_TO_SIP + FAILURE_TERMINATIONS |
| `backend/app/api/outbound_calls.py` | 270-340 | `_monitor_ultravox_call()` |
| `backend/app/api/outbound_calls.py` | 103-170 | `_monitor_outbound_channel()` (OpenAI) |
| `backend/app/api/v1/calls.py` | ~480-560 | Hangup handler + `_cancel_ultravox_via_ari()` |
| `backend/app/services/ultravox_provider.py` | 131-141 | SIP routing konfigürasyonu |
| `backend/app/services/openai_provider.py` | 168-186 | ARI çağrı başlatma |
| `asterisk/extensions.conf` | 64-83 | `[from-ultravox]` context (AMD U() ile) |
| `asterisk/extensions.conf` | 95-105 | `[ultravox-amd-check]` subroutine |
| `asterisk/extensions.conf` | 184-207 | `[ai-outbound]` context |
| `asterisk/extensions.conf` | 211-215 | `[amd_machine]` context |
| `asterisk/amd.conf` | 1-53 | AMD konfigürasyon parametreleri |
| `asterisk/pjsip.conf` | 103-139 | Ultravox SIP endpoint konfigürasyonu |
