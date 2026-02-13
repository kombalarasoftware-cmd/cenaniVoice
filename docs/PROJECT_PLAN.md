# 🎯 VoiceAI Platform - Proje Planı

> **OpenAI Realtime API ile Outbound Auto-Dialer Sistemi**
> 
> Modern, kullanışlı ve görsel açıdan etkileyici bir sesli AI agent platformu

---

## 📋 İçindekiler

1. [Proje Özeti](#-proje-özeti)
2. [Teknoloji Stack](#-teknoloji-stack)
3. [Tasarım Sistemi](#-tasarım-sistemi)
4. [Sayfa Yapısı](#-sayfa-yapısı)
5. [Özellikler](#-özellikler)
6. [Veritabanı Şeması](#-veritabanı-şeması)
7. [API Endpoints](#-api-endpoints)
8. [Aşamalar ve Timeline](#-aşamalar-ve-timeline)

---

## 🎯 Proje Özeti

### Vizyon
Kendi SIP altyapınızı kullanarak, Excel'den yüklenen telefon numaralarını otomatik olarak arayan, 
OpenAI Realtime API ile güçlendirilmiş sesli AI agent platformu.

### Ana Özellikler
- ✅ 50 eş zamanlı outbound çağrı
- ✅ Çok dilli destek (OpenAI'ın desteklediği tüm diller)
- ✅ Prompt Maker / Builder
- ✅ Müşteri ismiyle kişiselleştirilmiş hitap
- ✅ 3 modlu test sistemi (Chat, Voice Widget, Phone)
- ✅ Gerçek zamanlı ses animasyonları
- ✅ Dark/Light tema desteği
- ✅ Call recording & Transcription
- ✅ Human transfer
- ✅ Webhook entegrasyonları
- ✅ Detaylı raporlama

---

## 🛠 Teknoloji Stack

### Frontend
```
┌─────────────────────────────────────────────────────────┐
│  Next.js 14 (App Router)                                │
│  ├── TypeScript                                         │
│  ├── Tailwind CSS                                       │
│  ├── shadcn/ui (Component Library)                      │
│  ├── Framer Motion (Animasyonlar)                       │
│  ├── Zustand (State Management)                         │
│  ├── React Query (Data Fetching)                        │
│  ├── Socket.io Client (Real-time)                       │
│  └── Web Audio API (Ses Görselleştirme)                 │
└─────────────────────────────────────────────────────────┘
```

### Backend
```
┌─────────────────────────────────────────────────────────┐
│  FastAPI (Python 3.11+)                                 │
│  ├── SQLAlchemy (ORM)                                   │
│  ├── Alembic (Migrations)                               │
│  ├── Celery (Background Tasks)                          │
│  ├── Redis (Cache & Queue)                              │
│  ├── WebSockets (Real-time)                             │
│  ├── OpenAI SDK (Realtime API)                          │
│  └── Asterisk ARI (SIP Integration)                     │
└─────────────────────────────────────────────────────────┘
```

### Infrastructure
```
┌─────────────────────────────────────────────────────────┐
│  Docker & Docker Compose                                │
│  ├── PostgreSQL 16                                      │
│  ├── Redis 7                                            │
│  ├── Asterisk 20                                        │
│  ├── Nginx (Reverse Proxy)                              │
│  └── MinIO (Object Storage - Recordings)                │
└─────────────────────────────────────────────────────────┘
```

---

## 🎨 Tasarım Sistemi

### Renk Paleti

#### Light Mode
```css
:root {
  /* Primary - Modern Mor/İndigo */
  --primary-50: #f5f3ff;
  --primary-100: #ede9fe;
  --primary-200: #ddd6fe;
  --primary-300: #c4b5fd;
  --primary-400: #a78bfa;
  --primary-500: #8b5cf6;  /* Ana renk */
  --primary-600: #7c3aed;
  --primary-700: #6d28d9;
  --primary-800: #5b21b6;
  --primary-900: #4c1d95;

  /* Secondary - Cyan/Teal */
  --secondary-50: #ecfeff;
  --secondary-100: #cffafe;
  --secondary-200: #a5f3fc;
  --secondary-300: #67e8f9;
  --secondary-400: #22d3ee;
  --secondary-500: #06b6d4;  /* Ana renk */
  --secondary-600: #0891b2;
  --secondary-700: #0e7490;
  --secondary-800: #155e75;
  --secondary-900: #164e63;

  /* Accent - Amber/Gold */
  --accent-500: #f59e0b;

  /* Success */
  --success-500: #22c55e;

  /* Warning */
  --warning-500: #eab308;

  /* Error */
  --error-500: #ef4444;

  /* Neutral */
  --neutral-50: #fafafa;
  --neutral-100: #f4f4f5;
  --neutral-200: #e4e4e7;
  --neutral-300: #d4d4d8;
  --neutral-400: #a1a1aa;
  --neutral-500: #71717a;
  --neutral-600: #52525b;
  --neutral-700: #3f3f46;
  --neutral-800: #27272a;
  --neutral-900: #18181b;

  /* Background */
  --bg-primary: #ffffff;
  --bg-secondary: #f4f4f5;
  --bg-tertiary: #e4e4e7;

  /* Text */
  --text-primary: #18181b;
  --text-secondary: #52525b;
  --text-muted: #a1a1aa;
}
```

#### Dark Mode
```css
:root.dark {
  /* Primary - Daha parlak mor */
  --primary-500: #a78bfa;

  /* Secondary - Daha parlak cyan */
  --secondary-500: #22d3ee;

  /* Background */
  --bg-primary: #09090b;
  --bg-secondary: #18181b;
  --bg-tertiary: #27272a;

  /* Text */
  --text-primary: #fafafa;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;

  /* Glass Effect */
  --glass-bg: rgba(24, 24, 27, 0.8);
  --glass-border: rgba(255, 255, 255, 0.1);
}
```

### Typography
```css
/* Font Family */
--font-sans: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', monospace;

/* Font Sizes */
--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */
--text-3xl: 1.875rem;  /* 30px */
--text-4xl: 2.25rem;   /* 36px */
```

### Görsel Efektler

#### Glassmorphism
```css
.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
}
```

#### Gradient Backgrounds
```css
.gradient-primary {
  background: linear-gradient(135deg, var(--primary-500), var(--secondary-500));
}

.gradient-glow {
  background: radial-gradient(
    ellipse at center,
    rgba(139, 92, 246, 0.15) 0%,
    transparent 70%
  );
}
```

#### Ses Animasyonları (Voice Visualizer)
```css
/* Ses dalgası animasyonu */
@keyframes wave {
  0%, 100% { transform: scaleY(0.3); }
  50% { transform: scaleY(1); }
}

.voice-bar {
  animation: wave 0.5s ease-in-out infinite;
  animation-delay: calc(var(--i) * 0.1s);
}

/* Pulse animasyonu (konuşurken) */
@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; }
}

.voice-pulse {
  animation: pulse-ring 1.5s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}

/* Orbital animasyon (AI düşünürken) */
@keyframes orbit {
  from { transform: rotate(0deg) translateX(30px) rotate(0deg); }
  to { transform: rotate(360deg) translateX(30px) rotate(-360deg); }
}
```

---

## 📄 Sayfa Yapısı

```
app/
├── (auth)/
│   ├── login/
│   └── register/
│
├── (dashboard)/
│   ├── layout.tsx              # Dashboard layout (sidebar + header)
│   ├── page.tsx                # Ana dashboard
│   │
│   ├── campaigns/
│   │   ├── page.tsx            # Kampanya listesi
│   │   ├── new/page.tsx        # Yeni kampanya
│   │   └── [id]/
│   │       ├── page.tsx        # Kampanya detayı
│   │       ├── edit/page.tsx   # Kampanya düzenle
│   │       └── calls/page.tsx  # Kampanya çağrıları
│   │
│   ├── agents/
│   │   ├── page.tsx            # Agent listesi
│   │   ├── new/page.tsx        # Yeni agent
│   │   └── [id]/
│   │       ├── page.tsx        # Agent detayı & Editor
│   │       ├── test/page.tsx   # Test ekranı (3 mod)
│   │       └── prompts/page.tsx # Prompt versiyonları
│   │
│   ├── prompt-maker/
│   │   ├── page.tsx            # Prompt builder
│   │   └── templates/page.tsx  # Hazır şablonlar
│   │
│   ├── numbers/
│   │   ├── page.tsx            # Numara listeleri
│   │   ├── upload/page.tsx     # Excel upload
│   │   └── [listId]/page.tsx   # Liste detayı
│   │
│   ├── calls/
│   │   ├── page.tsx            # Tüm çağrılar
│   │   ├── live/page.tsx       # Canlı çağrılar
│   │   └── [id]/page.tsx       # Çağrı detayı & kayıt
│   │
│   ├── recordings/
│   │   ├── page.tsx            # Kayıt listesi
│   │   └── [id]/page.tsx       # Kayıt oynatıcı
│   │
│   ├── reports/
│   │   ├── page.tsx            # Rapor dashboard
│   │   ├── campaigns/page.tsx  # Kampanya raporları
│   │   └── export/page.tsx     # Rapor export
│   │
│   └── settings/
│       ├── page.tsx            # Genel ayarlar
│       ├── sip/page.tsx        # SIP ayarları
│       ├── webhooks/page.tsx   # Webhook ayarları
│       ├── api-keys/page.tsx   # API key yönetimi
│       └── team/page.tsx       # Takım yönetimi
│
└── api/                        # API Routes (Next.js)
    └── ...
```

---

## ✨ Özellikler (Detaylı)

### 1. Dashboard
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏠 Dashboard                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Quick Stats (Animated Cards) ────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │ │
│  │  │ 🔴 Active    │ │ 📊 Today     │ │ ✅ Success   │ │ ⏱️ Avg Time  │  │ │
│  │  │    Calls     │ │    Total     │ │    Rate      │ │   Duration   │  │ │
│  │  │              │ │              │ │              │ │              │  │ │
│  │  │     23       │ │   1,847      │ │   78.4%      │ │    2:34      │  │ │
│  │  │  ↑ 5 vs now  │ │  ↑ 12% vs y  │ │  ↑ 3.2%     │ │  ↓ 15s       │  │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Live Activity ──────────────────┐ ┌─ Campaign Performance ───────────┐ │
│  │                                  │ │                                  │ │
│  │  Real-time call waveform viz     │ │  Interactive chart               │ │
│  │  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~    │ │  📈 Line/Bar chart               │ │
│  │                                  │ │                                  │ │
│  │  Active Calls List               │ │  Filter: [Today ▼] [All ▼]       │ │
│  │  • +90 532... → Connected 2:34  │ │                                  │ │
│  │  • +90 535... → Ringing          │ │                                  │ │
│  │  • +90 542... → AI Talking       │ │                                  │ │
│  │                                  │ │                                  │ │
│  └──────────────────────────────────┘ └──────────────────────────────────┘ │
│                                                                             │
│  ┌─ Recent Campaigns ───────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  Campaign Name         Progress        Status       Actions          │  │
│  │  ─────────────────────────────────────────────────────────────────── │  │
│  │  Ödeme Hatırlatma     ████████░░ 78%   🟢 Running   [View] [Pause]  │  │
│  │  Anket Kampanyası     ██████████ 100%  ✅ Done      [View] [Report] │  │
│  │  Yeni Müşteri         ████░░░░░░ 34%   ⏸️ Paused    [View] [Resume] │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Agent Test Ekranı (3 Mod)

#### Mod 1: Chat Test
- Yazılı mesajlaşma ile test
- Real-time typing indicator
- Tool call görselleştirmesi
- Intent detection gösterimi
- Conversation flow tracking

#### Mod 2: Voice Widget Test
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🎙️ Voice Test                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                    ┌────────────────────────────────┐                       │
│                    │                                │                       │
│                    │     ╭──────────────────╮       │                       │
│                    │     │                  │       │                       │
│                    │     │   ◉ ◉ ◉ ◉ ◉ ◉   │  ← Animated voice bars        │
│                    │     │   ▏▎▍▌▋▊▉█▉▊▋▌▍▎▏│       │                       │
│                    │     │                  │       │                       │
│                    │     │      02:34       │       │                       │
│                    │     │                  │       │                       │
│                    │     ╰──────────────────╯       │                       │
│                    │                                │                       │
│                    │  ┌──────┐  ┌──────┐  ┌──────┐ │                       │
│                    │  │ 🔴   │  │ ⏸️   │  │ ⏹️   │ │                       │
│                    │  │ Rec  │  │Pause │  │ Stop │ │                       │
│                    │  └──────┘  └──────┘  └──────┘ │                       │
│                    │                                │                       │
│                    └────────────────────────────────┘                       │
│                                                                             │
│  Ses Animasyon Modları:                                                     │
│  • Waveform (Dalga formu)                                                   │
│  • Frequency Bars (Frekans çubukları)                                       │
│  • Circular Pulse (Dairesel nabız)                                          │
│  • Particle System (Parçacık sistemi)                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Mod 3: Phone Test
- Gerçek telefon numarası girişi
- Test müşteri verisi girişi
- Canlı çağrı takibi
- Kayıt ve transcript

### 3. Prompt Maker
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ✨ Prompt Maker                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Template Gallery ───────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  [💰 Ödeme] [📅 Randevu] [📞 Destek] [🛒 Satış] [📊 Anket] [+]       │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Builder ─────────────────────────┐ ┌─ Preview ───────────────────────┐ │
│  │                                   │ │                                  │ │
│  │  Step 1: Identity                 │ │  Generated Prompt               │ │
│  │  ┌─────────────────────────────┐  │ │  ─────────────────────────────  │ │
│  │  │ Agent Name: [___________]   │  │ │                                  │ │
│  │  │ Company:    [___________]   │  │ │  # Role & Objective             │ │
│  │  │ Role:       [___________▼]  │  │ │  Sen {{company}} şirketinin...  │ │
│  │  └─────────────────────────────┘  │ │                                  │ │
│  │                                   │ │  # Personality & Tone           │ │
│  │  Step 2: Style                    │ │  - Kişilik: Profesyonel...      │ │
│  │  ┌─────────────────────────────┐  │ │                                  │ │
│  │  │ Tone: [Pro] [Casual] [Warm] │  │ │  # Conversation Flow            │ │
│  │  │ Formality: ────○──────      │  │ │  1. Selamlama...                │ │
│  │  │ Empathy:   ──────○────      │  │ │  2. İhtiyaç belirleme...        │ │
│  │  └─────────────────────────────┘  │ │                                  │ │
│  │                                   │ │  [Copy] [Improve with AI]       │ │
│  │  Step 3: Flow                     │ │                                  │ │
│  │  ┌─────────────────────────────┐  │ └──────────────────────────────────┘ │
│  │  │ Drag & Drop Steps           │  │                                     │
│  │  │ [1. Greeting    ] ↕️        │  │                                     │
│  │  │ [2. Verify      ] ↕️        │  │                                     │
│  │  │ [3. Main Topic  ] ↕️        │  │                                     │
│  │  │ [+ Add Step]                │  │                                     │
│  │  └─────────────────────────────┘  │                                     │
│  │                                   │                                     │
│  └───────────────────────────────────┘                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Live Calls Monitor
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔴 Live Calls                                           23 Active Calls   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Call Grid ──────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐   │  │
│  │  │ 📞 +90 532 XXX    │ │ 📞 +90 535 XXX    │ │ 📞 +90 542 XXX    │   │  │
│  │  │                   │ │                   │ │                   │   │  │
│  │  │ ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁  │ │ ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁  │ │ ▁▃▅▇▅▃▁▃▅▇▅▃▁▃▅  │   │  │
│  │  │                   │ │                   │ │                   │   │  │
│  │  │ 02:34 │ 🟢 Active │ │ 00:12 │ 🔔 Ring  │ │ 01:45 │ 🟢 Active │   │  │
│  │  │ Campaign A        │ │ Campaign A        │ │ Campaign B        │   │  │
│  │  │                   │ │                   │ │                   │   │  │
│  │  │ [👁️ Monitor]      │ │ [⏸️ Cancel]       │ │ [👁️ Monitor]      │   │  │
│  │  └───────────────────┘ └───────────────────┘ └───────────────────┘   │  │
│  │                                                                       │  │
│  │  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐   │  │
│  │  │ ...more calls     │ │ ...               │ │ ...               │   │  │
│  │  └───────────────────┘ └───────────────────┘ └───────────────────┘   │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Veritabanı Şeması

### Core Tables

```sql
-- Kullanıcılar
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user', -- admin, user, viewer
    avatar_url VARCHAR(500),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Agentlar
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Voice Settings
    voice VARCHAR(50) DEFAULT 'marin',
    model VARCHAR(100) DEFAULT 'gpt-realtime',
    
    -- Language Settings
    primary_language VARCHAR(10) DEFAULT 'tr',
    additional_languages JSONB DEFAULT '[]',
    auto_detect_language BOOLEAN DEFAULT false,
    response_language_mode VARCHAR(20) DEFAULT 'same',
    
    -- Turn Detection
    turn_detection_type VARCHAR(20) DEFAULT 'semantic',
    turn_detection_threshold DECIMAL(3,2) DEFAULT 0.50,
    prefix_padding_ms INTEGER DEFAULT 300,
    silence_duration_ms INTEGER DEFAULT 500,
    
    -- Personalization
    use_customer_name BOOLEAN DEFAULT true,
    name_format VARCHAR(50) DEFAULT 'name_honorific', -- name, name_honorific, full_name, honorific_only
    gender_detection VARCHAR(20) DEFAULT 'auto',
    name_usage_frequency VARCHAR(20) DEFAULT 'key_moments',
    
    -- Prompt
    system_instructions TEXT,
    
    -- Tools
    tools JSONB DEFAULT '[]',
    transfer_number VARCHAR(50),
    
    -- Settings
    max_call_duration INTEGER DEFAULT 300,
    idle_timeout_ms INTEGER,
    
    status VARCHAR(20) DEFAULT 'draft', -- draft, active, archived
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Prompt Şablonları
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    language VARCHAR(10),
    description TEXT,
    template_content TEXT NOT NULL,
    variables JSONB DEFAULT '[]',
    tone_settings JSONB DEFAULT '{}',
    flow_steps JSONB DEFAULT '[]',
    is_system BOOLEAN DEFAULT false,
    is_public BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    rating DECIMAL(2,1),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Kampanyalar
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    agent_id UUID REFERENCES agents(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Settings
    concurrent_calls INTEGER DEFAULT 5,
    retry_attempts INTEGER DEFAULT 2,
    retry_delay_minutes INTEGER DEFAULT 60,
    
    -- Working Hours
    working_hours_enabled BOOLEAN DEFAULT false,
    working_hours_start TIME,
    working_hours_end TIME,
    working_days JSONB DEFAULT '[1,2,3,4,5]',
    timezone VARCHAR(50) DEFAULT 'Europe/Istanbul',
    
    -- Caller ID
    caller_id VARCHAR(50),
    
    -- Webhook
    webhook_url VARCHAR(500),
    webhook_events JSONB DEFAULT '[]',
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft', -- draft, scheduled, running, paused, completed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Stats
    total_numbers INTEGER DEFAULT 0,
    completed_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Numara Listeleri
CREATE TABLE number_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    file_name VARCHAR(255),
    total_count INTEGER DEFAULT 0,
    column_mapping JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Telefon Numaraları
CREATE TABLE phone_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_id UUID REFERENCES number_lists(id),
    campaign_id UUID REFERENCES campaigns(id),
    
    phone_number VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255),
    custom_data JSONB DEFAULT '{}',
    
    status VARCHAR(20) DEFAULT 'pending', 
    -- pending, queued, calling, connected, completed, failed, no_answer, busy, voicemail, dnc
    
    priority INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Çağrı Logları
CREATE TABLE call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number_id UUID REFERENCES phone_numbers(id),
    campaign_id UUID REFERENCES campaigns(id),
    agent_id UUID REFERENCES agents(id),
    
    -- Call Info
    asterisk_channel_id VARCHAR(255),
    openai_session_id VARCHAR(255),
    
    -- Timing
    initiated_at TIMESTAMP,
    ring_started_at TIMESTAMP,
    connected_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Result
    disposition VARCHAR(50), -- answered, no_answer, busy, failed, voicemail, transferred
    hangup_cause VARCHAR(100),
    transferred_to VARCHAR(50),
    
    -- Content
    recording_path VARCHAR(500),
    transcript TEXT,
    ai_summary TEXT,
    detected_intent VARCHAR(100),
    sentiment VARCHAR(20),
    outcome_tags JSONB DEFAULT '[]',
    
    -- Tool Usage
    tools_called JSONB DEFAULT '[]',
    
    -- Webhook
    webhook_sent BOOLEAN DEFAULT false,
    webhook_response JSONB,
    
    -- Cost
    estimated_cost DECIMAL(10,4),
    tokens_used INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Kayıtlar (Recordings)
CREATE TABLE recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_log_id UUID REFERENCES call_logs(id),
    
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    duration_seconds INTEGER,
    format VARCHAR(20),
    
    -- Transcription
    transcription_status VARCHAR(20), -- pending, processing, completed, failed
    transcription_text TEXT,
    transcription_segments JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Webhook Configurations
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    secret VARCHAR(255),
    events JSONB DEFAULT '[]',
    headers JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- SIP Trunks
CREATE TABLE sip_trunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    
    host VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 5060,
    transport VARCHAR(10) DEFAULT 'udp', -- udp, tcp, tls
    
    username VARCHAR(255),
    password_encrypted VARCHAR(500),
    
    caller_id VARCHAR(50),
    max_channels INTEGER DEFAULT 10,
    
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_phone_numbers_campaign ON phone_numbers(campaign_id);
CREATE INDEX idx_phone_numbers_status ON phone_numbers(status);
CREATE INDEX idx_call_logs_campaign ON call_logs(campaign_id);
CREATE INDEX idx_call_logs_created ON call_logs(created_at);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_agents_user ON agents(user_id);
```

---

## 🔌 API Endpoints

### Authentication
```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
GET    /api/auth/me
```

### Agents
```
GET    /api/agents                    # List agents
POST   /api/agents                    # Create agent
GET    /api/agents/:id                # Get agent
PUT    /api/agents/:id                # Update agent
DELETE /api/agents/:id                # Delete agent
POST   /api/agents/:id/duplicate      # Duplicate agent
POST   /api/agents/:id/test/chat      # Chat test
POST   /api/agents/:id/test/voice     # Voice test (WebSocket upgrade)
POST   /api/agents/:id/test/phone     # Phone test
```

### Campaigns
```
GET    /api/campaigns                 # List campaigns
POST   /api/campaigns                 # Create campaign
GET    /api/campaigns/:id             # Get campaign
PUT    /api/campaigns/:id             # Update campaign
DELETE /api/campaigns/:id             # Delete campaign
POST   /api/campaigns/:id/start       # Start campaign
POST   /api/campaigns/:id/pause       # Pause campaign
POST   /api/campaigns/:id/resume      # Resume campaign
POST   /api/campaigns/:id/stop        # Stop campaign
GET    /api/campaigns/:id/stats       # Get campaign stats
GET    /api/campaigns/:id/calls       # Get campaign calls
```

### Numbers
```
GET    /api/numbers/lists             # List number lists
POST   /api/numbers/lists             # Create list
GET    /api/numbers/lists/:id         # Get list
DELETE /api/numbers/lists/:id         # Delete list
POST   /api/numbers/upload            # Upload Excel
GET    /api/numbers/lists/:id/numbers # Get numbers in list
POST   /api/numbers/lists/:id/assign  # Assign to campaign
```

### Calls
```
GET    /api/calls                     # List calls
GET    /api/calls/live                # Get live calls
GET    /api/calls/:id                 # Get call details
GET    /api/calls/:id/recording       # Get recording
GET    /api/calls/:id/transcript      # Get transcript
POST   /api/calls/:id/transfer        # Transfer call
POST   /api/calls/:id/hangup          # Hangup call
```

### Recordings
```
GET    /api/recordings                # List recordings
GET    /api/recordings/:id            # Get recording
GET    /api/recordings/:id/audio      # Stream audio
GET    /api/recordings/:id/transcript # Get transcript
POST   /api/recordings/:id/transcribe # Request transcription
```

### Reports
```
GET    /api/reports/dashboard         # Dashboard stats
GET    /api/reports/campaigns/:id     # Campaign report
GET    /api/reports/agents/:id        # Agent performance
GET    /api/reports/export            # Export report
```

### Settings
```
GET    /api/settings                  # Get settings
PUT    /api/settings                  # Update settings
GET    /api/settings/sip              # Get SIP config
PUT    /api/settings/sip              # Update SIP config
GET    /api/settings/webhooks         # List webhooks
POST   /api/settings/webhooks         # Create webhook
PUT    /api/settings/webhooks/:id     # Update webhook
DELETE /api/settings/webhooks/:id     # Delete webhook
```

### Prompt Templates
```
GET    /api/templates                 # List templates
POST   /api/templates                 # Create template
GET    /api/templates/:id             # Get template
PUT    /api/templates/:id             # Update template
DELETE /api/templates/:id             # Delete template
POST   /api/templates/:id/use         # Use template
POST   /api/templates/generate        # AI generate prompt
POST   /api/templates/improve         # AI improve prompt
```

### WebSocket Endpoints
```
WS     /ws/calls/live                 # Live calls stream
WS     /ws/calls/:id/monitor          # Monitor specific call
WS     /ws/test/voice                 # Voice test session
```

---

## 📅 Aşamalar ve Timeline

### Phase 1: Foundation (Hafta 1-2)
```
□ Proje yapısı oluşturma
□ Docker Compose setup
□ PostgreSQL + Redis setup
□ FastAPI backend skeleton
□ Next.js frontend skeleton
□ Tailwind + shadcn/ui setup
□ Dark/Light tema altyapısı
□ Authentication (JWT)
□ Basic dashboard layout
```

### Phase 2: Core Features (Hafta 3-4)
```
□ Agent CRUD
□ Agent Editor UI
□ Prompt Maker UI
□ Prompt Templates
□ Number Lists
□ Excel Upload
□ Campaign CRUD
□ Campaign management
```

### Phase 3: Asterisk Integration (Hafta 5-6)
```
□ Asterisk Docker setup
□ SIP Trunk configuration
□ ARI integration
□ Originate calls
□ Call events handling
□ Audio bridge
```

### Phase 4: OpenAI Integration (Hafta 7-8)
```
□ OpenAI Realtime API integration
□ WebSocket session management
□ Audio streaming bridge
□ Tool calling
□ Human transfer
```

### Phase 5: Test Features (Hafta 9-10)
```
□ Chat test mode
□ Voice widget test mode
□ Phone test mode
□ Voice visualizations
□ Real-time transcript
□ Test insights panel
```

### Phase 6: Call Engine (Hafta 11-12)
```
□ Celery workers setup
□ Auto-dialer logic
□ Concurrent calls management
□ Retry logic
□ Call recording
□ Transcription
```

### Phase 7: Monitoring & Reports (Hafta 13-14)
```
□ Live calls dashboard
□ Campaign reports
□ Agent performance
□ Export functionality
□ Webhook system
```

### Phase 8: Polish & Deploy (Hafta 15-16)
```
□ UI animations
□ Performance optimization
□ Error handling
□ Documentation
□ Production deployment
□ Testing & QA
```

---

## 🎨 Görsel Animasyonlar

### Voice Visualizer Component
```typescript
// components/voice-visualizer.tsx

type VisualizerMode = 'waveform' | 'bars' | 'circular' | 'particles';

interface VoiceVisualizerProps {
  mode: VisualizerMode;
  isActive: boolean;
  audioLevel: number; // 0-1
  color?: string;
}

// Animasyonlar:
// 1. Waveform - Sinüs dalgası animasyonu
// 2. Bars - Frekans çubukları (equalizer)
// 3. Circular - Dairesel pulse efekti
// 4. Particles - Parçacık sistemi
```

### Call Card Animation
```typescript
// components/call-card.tsx

// States:
// - idle: Beklemede
// - ringing: Çalıyor (pulse animasyon)
// - connected: Bağlandı (yeşil glow)
// - talking: Konuşuyor (ses dalgaları)
// - ended: Bitti (fade out)
```

### Dashboard Animations
```typescript
// Stat kartları: CountUp animasyonu
// Grafikler: Staggered reveal
// Live feed: Slide-in animasyonu
// Kampanya progress: Smooth progress bar
```

---

## 📱 Responsive Breakpoints

```css
/* Mobile First */
sm: 640px   /* Small tablets */
md: 768px   /* Tablets */
lg: 1024px  /* Laptops */
xl: 1280px  /* Desktops */
2xl: 1536px /* Large screens */
```

---

## 🔐 Security

- JWT based authentication
- Rate limiting
- CORS configuration
- Input validation
- SQL injection protection
- XSS protection
- Encrypted passwords (bcrypt)
- Encrypted SIP credentials
- Audit logging
- RBAC (Role Based Access Control)

---

## 📝 Notlar

- Tüm text'ler i18n ready olacak (gelecekte çoklu dil desteği için)
- API versiyonlama yapılacak (/api/v1/)
- Error handling standardize edilecek
- Logging (structured JSON logs)
- Health check endpoints
- Graceful shutdown
- Database connection pooling
- Redis connection pooling

---

*Son güncelleme: 4 Şubat 2026*
