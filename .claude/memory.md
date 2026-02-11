# Project Memory

> Persistent knowledge store across chat sessions.
> Read at conversation start, updated when important discoveries are made.
> Portable — works with any project in any language.

## Project Info

- **Name**: VoiceAI Platform (Ultravox / cenaniVoice)
- **Repo**: https://github.com/kombalarasoftware-cmd/cenaniVoice.git
- **Branch**: main (single branch)
- **Purpose**: AI-powered outbound/inbound voice call platform with dual provider support
- **Stack**: Next.js 14 (frontend) + FastAPI (backend) + Asterisk PBX + PostgreSQL + Redis + Celery + MinIO
- **AI Providers**: OpenAI Realtime API + Ultravox API (pluggable via Provider Factory)
- **Deployment**: Docker Compose (dev + prod), Nginx reverse proxy with SSL

## Architecture Decisions

- [2026-02-08] Dual AI provider architecture: OpenAI (WebSocket audio bridge) + Ultravox (SIP-native)
- [2026-02-08] ViciDial-style hopper system for campaign dialing (DialList → DialListEntry → DialHopper)
- [2026-02-08] Universal Tool Registry: single source of truth, converts to OpenAI/Ultravox format
- [2026-02-08] Provider Factory pattern for pluggable AI providers
- [2026-02-08] Celery Beat for periodic tasks (campaign batching every 30s, callbacks every 5m)
- [2026-02-08] Circuit breaker per provider (5 failures → 30s cooldown)
- [2026-02-08] Atomic SQL increments for campaign stats (no race conditions)
- [2026-02-08] pgvector for RAG/document embeddings in PostgreSQL
- [2026-02-08] Structured JSON logging with request ID tracing (structlog)
- [2026-02-11] Moving to GitHub-based development with server deployment and testing

## Known Issues & Gotchas

- Ultravox SIP password must match `pjsip.conf [ultravox-auth]` exactly
- AudioSocket requires Asterisk 20+ for native 24kHz slin codec
- Circuit breaker state is in-memory per worker (not distributed across workers)
- CORS must be explicitly whitelisted in production (never use `*`)
- MinIO buckets must be pre-created before first upload
- PostgreSQL needs pgvector extension installed for RAG features
- `.env.prod` exists in repo root (untracked) — contains real API keys, never commit
- Asterisk `extensions.conf` and `pjsip.conf` have hardcoded IPs that need env var substitution
- Frontend uses relative API URLs (`/api/`) for nginx proxy in production
- Entrypoint scripts must use LF line endings (not CRLF) for Linux containers

## Environment & Setup

- **Python**: 3.11-slim (Docker)
- **Node.js**: 18-alpine (Docker)
- **PostgreSQL**: 16 with pgvector extension
- **Redis**: 7 (Celery broker + cache)
- **Asterisk**: 20 (SIP/ARI)
- **MinIO**: S3-compatible object storage
- **Nginx**: 1.25 (SSL termination, rate limiting)
- **Config files**: `.env.example` (template), `.env.prod` (production secrets — untracked)
- **DB migrations**: Alembic (`backend/alembic/`)
- **Dev**: `docker-compose.yml` (hot reload, exposed ports)
- **Prod**: `docker-compose.prod.yml` (4 workers, SSL, no reload)

## Conventions & Patterns

- **API versioning**: `/api/v1/...`
- **Auth**: JWT tokens with bcrypt, role-based (ADMIN, MANAGER, OPERATOR)
- **Backend structure**: `app/api/v1/` (routes) → `app/services/` (business logic) → `app/models/` (ORM)
- **Frontend structure**: Next.js App Router, `src/components/` (ui, agents, call, dashboard, providers)
- **UI library**: shadcn/ui (Radix) + Tailwind CSS
- **Data fetching**: TanStack React Query
- **Forms**: React Hook Form + Zod
- **Commit style**: Conventional Commits (feat/fix/refactor/perf/chore/docs/security)
- **Language policy**: ALL text in English (UI, comments, logs, API) — no Turkish in code
- **Middleware order**: RequestID → SecurityHeaders → BodySizeLimit → RateLimit → CORS

## Key Files

- `backend/app/main.py` — FastAPI entry point, middleware stack
- `backend/app/core/config.py` — Pydantic settings (all env vars)
- `backend/app/core/database.py` — SQLAlchemy async session
- `backend/app/models/models.py` — All ORM models (~50 tables)
- `backend/app/api/v1/` — All API route files (agents, campaigns, calls, tools, auth, webhooks...)
- `backend/app/api/router.py` — Router aggregator
- `backend/app/services/provider_factory.py` — AI provider selection
- `backend/app/services/tool_registry.py` — Universal tool definitions (25+ tools)
- `backend/app/services/ultravox_provider.py` — Ultravox call implementation
- `backend/app/services/openai_provider.py` — OpenAI Realtime implementation
- `backend/app/services/asterisk_ari.py` — Asterisk ARI integration
- `backend/app/tasks/celery_tasks.py` — Background jobs (make_call, transcribe, etc.)
- `backend/requirements.txt` — Python dependencies
- `frontend/src/app/` — Next.js pages (App Router)
- `frontend/src/components/` — React components
- `frontend/src/lib/api.ts` — API client
- `frontend/package.json` — Node dependencies
- `asterisk/extensions.conf` — Dialplan
- `asterisk/pjsip.conf` — SIP config
- `nginx/nginx.conf` — Reverse proxy + SSL
- `docker-compose.yml` — Dev environment
- `docker-compose.prod.yml` — Production environment
- `.env.example` — Environment variable template

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
| celery-worker | — | — | Background tasks |
| celery-beat | — | — | Scheduler |

## API Endpoints Summary

- **Auth**: register, login, logout, me
- **Agents**: CRUD + test (chat/voice/phone)
- **Campaigns**: CRUD + start/pause/resume/stop
- **Calls**: list, live, details, transfer, hangup
- **Tools** (Ultravox webhooks): end-call, transfer, callback, payment, lead, appointment, survey, tags, search
- **Numbers**: upload Excel, list management
- **Webhooks**: Ultravox events, AMD results
- **Health**: /health (liveness), /ready (readiness)

## Recent Changes

- [2026-02-11] Full project analysis stored in memory for ongoing development
- [2026-02-08] Initialized generic Memory, Hooks, and Custom Commands systems
- [2026-02-08] LF line endings fix for Docker entrypoint scripts
- [2026-02-08] Asterisk IP config moved to env vars
- [2026-02-08] Frontend API URLs changed to relative for nginx proxy
- [2026-02-08] Production deployment config added (docker-compose.prod.yml, nginx SSL)
- [2026-02-08] Ultravox call hangup fix (correct API endpoint + Redis auth)
- [2026-02-08] Security: replaced optional auth with required auth on all endpoints
- [2026-02-08] Comprehensive platform overhaul: security, ViciDial autodialer, Excel upload
- [2026-02-08] Dual provider support (OpenAI + Ultravox), universal tool registry, AMD, cost tracking
