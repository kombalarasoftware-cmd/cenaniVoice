# VoiceAI Platform

🎯 **AI-powered Voice Agent Platform with OpenAI Realtime API**

Modern, kullanışlı ve görsel açıdan etkileyici bir sesli AI agent platformu.

## ✨ Özellikler

- 📞 **50 Eş Zamanlı Çağrı** - Outbound auto-dialer
- 🌍 **Çok Dilli Destek** - OpenAI'ın desteklediği tüm diller
- 🎨 **Prompt Maker** - Görsel prompt builder
- 👤 **Kişiselleştirme** - Müşteri ismiyle hitap
- 🧪 **3 Modlu Test** - Chat, Voice Widget, Phone Test
- 🎵 **Ses Animasyonları** - Real-time voice visualizer
- 🌓 **Dark/Light Tema** - Modern tasarım
- 📊 **Detaylı Raporlama** - Dashboard ve analytics
- 🔗 **Webhook Entegrasyonu** - Dış sistemlerle bağlantı

## 🛠️ Teknoloji Stack

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- Framer Motion

### Backend
- FastAPI (Python)
- PostgreSQL
- Redis
- Celery

### Infrastructure
- Docker & Docker Compose
- Asterisk PBX
- MinIO (Object Storage)

## 🚀 Başlangıç

### Gereksinimler
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### Kurulum

```bash
# Repository'yi klonla
git clone <repo-url>
cd voiceai-platform

# Environment dosyasını oluştur
cp .env.example .env

# .env dosyasını düzenle
# - OPENAI_API_KEY
# - SIP_TRUNK_* ayarları
# - Diğer gerekli değişkenler

# Docker ile başlat
docker-compose up -d

# Frontend development
cd frontend
npm install
npm run dev

# Backend development
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Erişim
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

## 📖 Dokümantasyon

Detaylı dokümantasyon için [PROJECT_PLAN.md](./docs/PROJECT_PLAN.md) dosyasına bakın.

## 📄 Lisans

MIT License
