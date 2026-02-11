# Project Memory

## Project Info
- **Name**: VoiceAI Platform (Ultravox / cenaniVoice)
- **Repo**: https://github.com/kombalarasoftware-cmd/cenaniVoice.git
- **Branch**: main (single branch)

## Architecture Decisions
- [2026-02-08] Dual AI provider: OpenAI (WebSocket audio bridge) + Ultravox (SIP-native)
- [2026-02-08] ViciDial-style hopper system: DialList → DialListEntry → DialHopper
- [2026-02-08] Universal Tool Registry: single source, converts to OpenAI/Ultravox format
- [2026-02-08] Provider Factory pattern for pluggable AI providers
- [2026-02-08] Celery Beat for periodic tasks (campaign batching 30s, callbacks 5m)
- [2026-02-08] Circuit breaker per provider (5 failures → 30s cooldown)
- [2026-02-08] Atomic SQL increments for campaign stats (no race conditions)
- [2026-02-08] pgvector for RAG/document embeddings
- [2026-02-08] Structured JSON logging with request ID tracing (structlog)
- [2026-02-11] GitHub-based development with server deployment and testing

## Known Gotchas
- Ultravox SIP password must match `pjsip.conf [ultravox-auth]` exactly
- AudioSocket requires Asterisk 20+ for native 24kHz slin codec
- Circuit breaker state is in-memory per worker (not distributed)
- CORS must be explicitly whitelisted in production (never `*`)
- MinIO buckets must be pre-created before first upload
- PostgreSQL needs pgvector extension for RAG features
- `.env.prod` in repo root (untracked) — contains real API keys, never commit
- Asterisk configs have hardcoded IPs that need env var substitution
- Frontend uses relative API URLs (`/api/`) for nginx proxy in production
- Entrypoint scripts must use LF line endings (not CRLF) for Linux containers

## Environment
- Python 3.11-slim | Node.js 18-alpine | PostgreSQL 16 + pgvector | Redis 7 | Asterisk 20 | MinIO | Nginx 1.25
- Config: `.env.example` (template), `.env.prod` (secrets — untracked)
- DB migrations: Alembic (`backend/alembic/`)
- Dev: `docker-compose.yml` | Prod: `docker-compose.prod.yml` (4 workers, SSL)

## Key Files
- `backend/app/main.py` — FastAPI entry, middleware stack
- `backend/app/core/config.py` — Pydantic Settings (all env vars)
- `backend/app/models/models.py` — All ORM models (~50 tables)
- `backend/app/services/provider_factory.py` — AI provider selection
- `backend/app/services/tool_registry.py` — Universal tool definitions (25+ tools)
- `backend/app/services/ultravox_provider.py` — Ultravox call implementation
- `backend/app/services/openai_provider.py` — OpenAI Realtime implementation
- `backend/app/services/asterisk_ari.py` — Asterisk ARI integration
- `backend/app/tasks/celery_tasks.py` — Background jobs
- `frontend/src/lib/api.ts` — API client
- `asterisk/extensions.conf` / `pjsip.conf` — SIP config
- `nginx/nginx.conf` — Reverse proxy + SSL

## Services & Ports (Docker)
| Service | Dev Port | Internal | Notes |
|---------|----------|----------|-------|
| frontend | 3000 | 3000 | Next.js |
| backend | 8000 | 8000 | FastAPI (uvicorn) |
| postgres | 5432 | 5432 | PostgreSQL 16 + pgvector |
| redis | 6379 | 6379 | Celery broker + cache |
| asterisk | 5060/udp, 8088 | 5060, 8088 | SIP + ARI |
| minio | 9000, 9001 | 9000 | S3 API + Console |
| nginx | 80, 443 | — | Production only |

## API Endpoints
- **Auth**: register, login, logout, me
- **Agents**: CRUD + test (chat/voice/phone)
- **Campaigns**: CRUD + start/pause/resume/stop
- **Calls**: list, live, details, transfer, hangup
- **Tools**: end-call, transfer, callback, payment, lead, appointment, survey, tags, search
- **Numbers**: upload Excel, list management
- **Webhooks**: Ultravox events, AMD results
- **Health**: /health (liveness), /ready (readiness)

## Recent Changes
- [2026-02-11] Claude Code configuration modernized (native hooks, skills, rules, agents)
- [2026-02-11] Full project analysis stored for ongoing development
- [2026-02-08] Complete platform overhaul: security, ViciDial autodialer, dual provider, universal tool registry
