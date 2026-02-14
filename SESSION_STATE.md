# VoiceAI Platform — Session State (2026-02-15)
> Bu dosya bir sonraki oturumda kaldığımız yerden devam etmek için kayıt altına alınmıştır.

## Server & Connection Info
- **Server**: `37.27.119.79`, SSH port `4323`, user `askar`, path `/opt/voiceai`
- **GitHub**: `kombalarasoftware-cmd/cenaniVoice`, branch `main`
- **HEAD commit**: `76c3a19` (fix: restore audio detection)
- **Docker**: `docker compose -f docker-compose.yml -f docker-compose.prod.yml` (ALWAYS both files)
- **Backend/Bridge**: Volume-mounted → `restart` sufficient (no `--build` needed)
- **Frontend**: Needs `--build` flag when changed
- **Admin Login**: `cmutlu2006@hotmail.com` / `Speakmaxi2026!`
- **PostgreSQL**: user `postgres`, password `vps2hqifrnBI7aFdEuA3cjKLHmY6o8MX`, db `voiceai`
- **Redis Password**: `P8yAqolR6MCdD9h1mXSnJwW4EfUHg57s`
- **Domain**: `one.speakmaxi.com`
- **Alembic version**: `012`

## User Profile
- Kullanıcı Türkçe konuşuyor, teknik bilgisi az
- Ondan teknik sorular sorma
- Web UI'da Türkçe YASAK (İngilizce)
- Kod/commit/değişken isimleri İngilizce

## Current Work: xAI / Grok Ses Kalitesi İyileştirmeleri

### Problem
xAI Grok (Agent #3, Dr. Ayşe - Randevu Asistanı, voice=Ara, model=grok-2-realtime, lang=tr)
- Türkçe konuşmayı doğru anlamıyordu ("Do I want to..." gibi İngilizce çıktılar)
- Kullanıcı konuşmaya başladığında AI hemen susmuyordu
- Genel olarak "geç duyuyor, geç algılıyor" şikayetleri

### Yapılan Düzeltmeler (Bu Oturum, Kronolojik)

#### 1. VAD/Audio İyileştirmeleri (commit `f639ea9`)
- Gemini VAD Configuration (AutomaticActivityDetection)
- Bridge default alignment (5 location)
- Provider capabilities update for Gemini
- Provider-specific optimal defaults
- OpenAI adaptive VAD

#### 2. Gemini languageCode Hotfix (commit `55015f0`)
- `languageCode` kaldırıldı — Gemini bunu desteklemiyordu

#### 3. xAI Session Config İlk Deneme (commit `e297126`)
- model, temperature, modalities eklendi → STT'yi bozdu

#### 4. xAI Revert (commit `b879ce8`)
- Belgelenmemiş parametreler kaldırıldı

#### 5. xAI Turkish STT Fix (commit `0f21ca9`)
- **PromptBuilder Language Preamble**: Instructions'ın EN BAŞINA bilingual (Türkçe+İngilizce) dil direktifi eklendi (`_add_language_preamble()` metodu, Layer 0, sadece xAI için)
- **input_audio_transcription.language**: xAI session config'e `"tr"` dil ipucu eklendi
- Sonuç: Transcript'ler artık Türkçe geliyor (önceki "Do I want to..." yerine)

#### 6. Latency Reduction (commit `36fef47`)
- Input buffer: 100ms → 40ms (60ms gecikme azaltması)
- Output buffer: 40ms → 20ms (ilk ses daha hızlı)
- Silence flush: barge-in anında 60ms sessizlik pompası

#### 7. Redis Batch + xAI Pass-through (commit `0aacd85`)
- Redis audio save: Bellekte biriktirip ~1 saniyede bir toplu yazma (25/s → 1/s Redis ops)
- "Too many connections" hatası düzeltildi
- xAI input buffer: 40ms → 20ms (tek chunk, sıfır bekleme)

#### 8. Instant Barge-in (commit `1d0f2e2`)
- Output pacer döngüsünde barge-in kontrolü (her chunk'tan önce)
- TCP SO_SNDBUF 128KB → 8KB azaltma
- Silence flush 60ms → 300ms artırma

#### 9. Audio Detection Restore (commit `76c3a19`) — EN SON
- SO_SNDBUF kaldırıldı (backpressure input ses yolunu blokluyordu)
- Silence flush 300ms → 100ms (5 frame, drain() yok)
- drain() kaldırıldı barge-in'den (event loop bloklanmasını önler)
- Output pacer'daki barge-in kontrolü KORUNUYOR

### Mevcut Durum (Son Aramanın Analizi)
Son arama (commit 76c3a19 deploy sonrası) henüz test EDİLMEDİ.
Önceki arama (`48dd9a07`): Transcript'lerde "..." ile başlayan eksik kelimeler vardı (300ms silence + drain backpressure sorunu).
Bu sorun `76c3a19` ile düzeltildi (100ms silence, drain yok), ama test bekleniyor.

### Hâlâ Var Olan Sorunlar
1. **MinIO kayıt hatası**: `InvalidAccessKeyId` — ses kaydı MinIO'ya kaydedilemiyor. Bu ayrı bir sorun, acil değil.
2. **xAI Grok Türkçe kalitesi**: Telefon ses kalitesi (8kHz upsampled to 24kHz) nedeniyle xAI'nin auto-detect'i mükemmel değil. Bazı kısa cümlelerde hâlâ garip çeviri olabiliyor. OpenAI bu konuda daha iyi.
3. **Susma hızı vs duyma kalitesi dengesi**: Silence flush artırınca AI susuyor ama kullanıcı sesini kaçırıyor. Azaltınca duyuyor ama geç susuyor. 100ms + drain-free şu an en iyi denge noktası.

## Önemli Dosyalar ve Değişiklikler

### `backend/app/services/asterisk_bridge.py` (~3420 satır)
- Ana AudioSocket ↔ AI provider köprüsü
- Buffer ayarları: input=40ms (xAI=20ms), output=20ms
- xAI barge-in: `_xai_barge_in` flag + output pacer loop check + 100ms silence (drain yok)
- Greeting protection: `_greeting_done` flag
- `save_audio_to_redis()`: Memory batch (48KB/~1s threshold), max 3 hata logu
- xAI session config: voice, instructions, input_audio_transcription.language, turn_detection (server_vad), audio (pcm24k), tools
- OpenAI session config: modalities, voice, pcm16, instructions, temperature, turn_detection (semantic_vad/server_vad), input_audio_transcription (model+language), tools, noise_reduction

### `backend/app/services/prompt_builder.py` (~480 satır)
- Universal prompt builder
- `_add_language_preamble()`: xAI-only Layer 0 — bilingual dil direktifi
- `_NATIVE_LANGUAGE_NAMES`: tr→Türkçe, de→Deutsch, etc.
- `_NATIVE_LANGUAGE_DIRECTIVES`: tam cümle halinde dil yönergeleri
- Language enforcement ayrıca `_add_voice_rules()` içinde (gemini+xai)

### `backend/app/core/provider_capabilities.py` (150 satır)
- xAI: temperature=False, turn_detection=False, all VAD params=False

### `backend/app/api/v1/agents.py` (~1031 satır)
- xAI optimal defaults: server_vad, medium eagerness, 0.5 threshold, 800ms silence

## AI Provider Bilgileri

### xAI / Grok
- WebSocket: `wss://api.x.ai/v1/realtime`
- Desteklenen session params: voice, instructions, turn_detection, audio, tools
- 100+ dil, auto-detection, Turkish resmi olarak destekleniyor
- server_vad only (semantic_vad yok, threshold/padding yok)
- response.cancel GÖNDERMEYİN — conversation state'i bozuyor
- Twilio telephony örneğinde `audio/pcmu` (G.711) kullanılıyor — biz `audio/pcm` 24kHz kullanıyoruz

### OpenAI
- WebSocket: `wss://api.openai.com/v1/realtime`
- Full session params desteği (modalities, temperature, turn_detection, vad parametreleri, noise_reduction)
- response.cancel destekliyor
- semantic_vad + server_vad destekliyor
- Adaptive VAD (bridge otomatik ayarlıyor)

### Gemini
- WebSocket: Gemini Live API
- AutomaticActivityDetection ile VAD
- languageCode DESTEKLEMİYOR (kaldırıldı)

## Deploy Komutları (Kopyala-Yapıştır)
```bash
# Commit + Push + Deploy (backend/bridge)
cd d:\ultravox && git add -A && git commit -m "fix: description" && git push origin main
ssh -p 4323 askar@37.27.119.79 "cd /opt/voiceai && git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml restart asterisk-bridge"

# Frontend deploy (--build gerekli)
ssh -p 4323 askar@37.27.119.79 "cd /opt/voiceai && git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build frontend"

# Log kontrol
ssh -p 4323 askar@37.27.119.79 "docker compose -f /opt/voiceai/docker-compose.yml -f /opt/voiceai/docker-compose.prod.yml logs asterisk-bridge --tail=200"
```

## Olası Sonraki Adımlar
1. **Test**: commit `76c3a19` deploy edildi ama henüz test edilmedi. Kullanıcıdan test araması yapması bekleniyor.
2. **Eğer hâlâ sorun varsa**: `audio/pcmu` (G.711 μ-law) formatını xAI için denemek — xAI'nin telephony örneklerinde bu format kullanılıyor.
3. **MinIO hatası**: InvalidAccessKeyId düzeltmesi (ayrı iş).
4. **Fallback strateji**: xAI Türkçe yeterince iyi olmuyorsa, OpenAI Realtime'ı Türkçe aramalarda kullanmayı önermek.

## Git Log (Son 10 Commit)
```
76c3a19 fix: restore audio detection - reduce silence flush, remove SO_SNDBUF
1d0f2e2 fix: instant barge-in - stop AI audio immediately when user speaks
0aacd85 perf: batch Redis audio saves + xAI pass-through buffer
36fef47 perf: reduce audio latency for faster speech detection
0f21ca9 fix: improve xAI Turkish STT with language preamble and transcription hint
b879ce8 fix: revert xAI session to documented params only
e297126 fix: improve xAI Grok language detection and session config
55015f0 fix: remove unsupported languageCode from Gemini inputAudioTranscription
f639ea9 feat: comprehensive provider VAD/audio improvements
```
