# Project Memory

## Project Info
- **Name**: VoiceAI Platform (Ultravox / cenaniVoice)
- **Repo**: https://github.com/kombalarasoftware-cmd/cenaniVoice.git (PUBLIC)
- **Branch**: main (single branch)
- **Domain**: speakmaxi.com (5 subdomains)
- **Server**: Hetzner 37.27.119.79 | Ubuntu 24.04 | 16 vCPU | 62GB RAM
- **SSH**: Port 4323, user `askar`

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
- [2026-02-11] Ownership-based authorization: all data filtered by Agent/Campaign.owner_id
- [2026-02-11] Admin role check for system settings (UserRole.ADMIN)
- [2026-02-12] Universal PromptBuilder: centralized 4-layer prompt system replacing 5 duplicate builders

## Known Gotchas
- Ultravox SIP password must match `pjsip.conf [ultravox-auth]` exactly
- AudioSocket requires Asterisk 20+ for native 24kHz slin codec
- Circuit breaker state is in-memory per worker (not distributed)
- CORS must be explicitly whitelisted in production (never `*`)
- MinIO buckets must be pre-created before first upload
- PostgreSQL needs pgvector extension for RAG features
- `.env.prod` in repo root (untracked) — contains real API keys, never commit
- Frontend uses relative API URLs (`/api/`) for nginx proxy in production
- Entrypoint scripts must use LF line endings (not CRLF) for Linux containers
- audio_bridge.py has i18n tool responses with `"tr"/"de"/"en"` keys — these are intentional multilingual, DO NOT translate
- SIP trunk provider: MUTLU TELEKOM
- GitHub repo is PUBLIC — never commit secrets

## Environment
- Python 3.11-slim | Node.js 18-alpine | PostgreSQL 16 + pgvector | Redis 7 | Asterisk 20 | MinIO | Nginx 1.25
- Config: `.env.example` (template), `.env.prod` (secrets — untracked)
- DB migrations: Alembic (`backend/alembic/`)
- Dev: `docker-compose.yml` | Prod: `docker-compose.prod.yml` (4 workers, SSL)

## Server Deployment (37.27.119.79)
- 16 Docker containers running (all services + celery workers + beat)
- SSL via Let's Encrypt (certbot auto-renew)
- UFW firewall active, fail2ban on SSH
- Subdomains: speakmaxi.com, app.speakmaxi.com, api.speakmaxi.com, storage.speakmaxi.com, pg.speakmaxi.com

## Key Files
- `backend/app/main.py` — FastAPI entry, middleware stack
- `backend/app/core/config.py` — Pydantic Settings (all env vars, no REDIS_PASSWORD field)
- `backend/app/models/models.py` — All ORM models (~50 tables), UserRole enum (ADMIN/MANAGER/OPERATOR)
- `backend/app/services/provider_factory.py` — AI provider selection
- `backend/app/services/tool_registry.py` — Universal tool definitions (25+ tools)
- `backend/app/services/audio_bridge.py` — OpenAI Realtime WebSocket bridge (large file, ~2000 lines)
- `backend/app/services/ultravox_provider.py` — Ultravox call implementation
- `backend/app/services/openai_provider.py` — OpenAI Realtime implementation
- `backend/app/services/asterisk_ari.py` — Asterisk ARI integration
- `backend/app/services/prompt_builder.py` — Universal 4-layer prompt builder (PromptContext + PromptBuilder)
- `backend/app/services/prompt_constants.py` — Shared prompt constants (titles, AMD, voice rules)
- `backend/app/services/minio_service.py` — MinIO file storage (uses settings.REDIS_URL)
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
| asterisk | **5043**/udp, 8088 | 5043, 8088 | SIP (changed from 5060) + ARI |
| minio | 9000, 9001 | 9000 | S3 API + Console |
| nginx | 80, 443 | — | Production only |

## API Endpoints
- **Auth**: register, login, logout, me
- **Agents**: CRUD + test (chat/voice/phone)
- **Campaigns**: CRUD + start/pause/resume/stop
- **Calls**: list, live, details, transfer, hangup, tags, recording
- **Tools**: end-call, transfer, callback, payment, lead, appointment, survey, tags, search
- **Numbers**: upload Excel, list management
- **Surveys**: list, stats, detail, delete (all ownership-filtered)
- **Leads**: list, stats, detail, update, delete (all ownership-filtered)
- **Appointments**: list, stats, detail, update, delete, cancel, complete (all ownership-filtered)
- **Reports**: AI overview, sentiment trend, quality score, tags, callbacks, agent comparison (auth required)
- **Settings**: SIP trunks (owner-filtered), API keys (owner-filtered), general (admin-only write), OpenAI test
- **Documents**: upload, list, delete, search (agent-ownership checked)
- **Webhooks**: Ultravox events, AMD results
- **Health**: /health (liveness), /ready (readiness)

## Security Fixes Applied [2026-02-11]
1. `.gitignore` — corrupted UTF-16 lines cleaned, `.env.prod` rules added
2. `minio_service.py` — REDIS_PASSWORD AttributeError → use REDIS_URL
3. `schemas.py` — CallTagsResponse.call_id type: int → str
4. `settings.py` — sync OpenAI → AsyncOpenAI; admin role check on PUT /general
5. `appointments.py` — ownership filter via Agent/Campaign outerjoin
6. `leads.py` — ownership filter via Agent/Campaign outerjoin
7. `surveys.py` — ownership checks on all 5 endpoints
8. `reports.py` — auth added to /costs/comparison; Turkish docstrings → English
9. `layout.tsx` — JWT validation bypass fixed (proper catch block)
10. `login/page.tsx` — JWT payload decode for user_name/email in localStorage
11. `tools.py` — 5x str(e) exposure removed
12. `audio_bridge.py` — 7x str(e) removed, ~30 Turkish messages → English
13. `ultravox_provider.py` — str(e) exposure removed
14. `extensions.conf` — all Turkish comments/messages → English
15. User applied: SIP port 5060→5043, SSH port 22→4323, ARI allowed_origins restricted, anonymous endpoint removed, Docker port isolation, env var passwords

## Remaining Server-Side Tasks
- SSH: PasswordAuthentication → no, PermitRootLogin → no
- Asterisk: fail2ban jail for SIP port 5043
- SIP credentials still in plaintext in pjsip.conf (consider env var substitution)

## Claude Code Configuration
- **Agents** (4): security-reviewer, code-reviewer, debugger, frontend-developer — all with `memory: user`, `maxTurns`, `permissionMode`
- **Skills** (14): review, security, test, deploy, refactor, changelog, fix-issue, interview, cascade-edit, create-pr, todo-scan, space, visual-dev, design-inspiration
- **Hooks** (11 active): SessionStart, PreToolUse (lint-check + filter-test-output), PostToolUse (python-check + ruff-check + cascade-detect), Notification, Stop (stop-check + todo-check), PreCompact, SessionEnd
- **Rules** (9): backend-python, frontend-react, frontend-design, security, docker-infra, api-routes, celery-tasks, database-models, react-components
- **MCP**: context7 (library docs, cmd /c wrapper for Windows)
- **Plugins** (8): GitHub, Playwright, Context7, Sentry, Figma, Pyright LSP, TypeScript LSP, Superpowers
- **Copilot Integration**: copilot-instructions.md, path-specific instructions (python, typescript), copilot-setup-steps.yml, 4 custom agents, Copilot CLI v1.2.0
- **GitHub Config**: Secret scanning + push protection, Dependabot alerts + auto-fix, CODEOWNERS, issue templates, PR template, SECURITY.md, 9 custom labels, dependabot.yml
- **Spaces**: `.claude/spaces/` for task-specific context (Copilot Spaces equivalent)
- **Status line**: Custom script showing model, branch, context%, cost, lines changed
- **File suggestion**: Custom @ autocomplete with priority extensions and skip dirs
- **Output styles**: `engineering.md` — structured technical responses
- **Keybindings**: Custom shortcuts (Ctrl+E editor, Ctrl+P model picker, Ctrl+Shift+T thinking, Ctrl+S stash)
- **CI/CD**: GitHub Actions CI + Claude Code PR Review + Copilot Setup Steps
- **Agent SDK scripts**: batch-migrate.sh, review-pr.sh, extract-api.sh
- **DevContainer**: `.devcontainer/devcontainer.json` (Python 3.11, Node 18, PostgreSQL, Redis, gh CLI)
- **$CLAUDE_PROJECT_DIR bug**: Does NOT expand on Windows cmd.exe — use relative paths in hook commands

## Recent Changes
- [2026-02-12] Universal PromptBuilder: centralized prompt_builder.py + prompt_constants.py replacing 5 duplicate builders (openai_provider, openai_realtime, ultravox_provider, asterisk_bridge, outbound_calls). 10-section standard: Role, Environment, Tone, Goal, Guardrails, Tools, Instructions, Conversation Flow, Safety & Escalation, Language. Prompt Maker aligned, ElevenLabs references removed.
- [2026-02-12] Visual design system: visual-dev skill (Playwright feedback loop), design-inspiration skill, frontend-design.md rule, framer-motion installed, tailwind enhanced (float, gradient-shift, blur-in, glassmorphism), CLAUDE.md design philosophy added
- [2026-02-11] Copilot features adapted to Claude Code: cascade-edit, create-pr, todo-scan, space skills; ruff-check, cascade-detect, todo-check hooks; 4 granular path-scoped rules
- [2026-02-11] GitHub Copilot integration: copilot-instructions.md, path-specific instructions, copilot-setup-steps.yml, 4 custom agents, Copilot CLI installed
- [2026-02-11] GitHub repo hardened: secret scanning, Dependabot, CODEOWNERS, issue/PR templates, SECURITY.md, 9 labels, description + 8 topics
- [2026-02-11] Advanced features: Sentry/Figma plugins, PreCompact/SessionEnd hooks, interview skill, Agent SDK scripts, DevContainer
- [2026-02-11] Full Claude Code feature implementation: status line, file suggestion, output styles, keybindings, LSP plugins, GitHub Actions review
- [2026-02-11] Claude Code 23-item gap analysis applied: agent memory, skill allowed-tools, hook system (5 events), model config
- [2026-02-11] Comprehensive security audit + 18 code fixes applied
- [2026-02-11] Full Turkish → English translation in tool responses and docstrings
- [2026-02-11] Ownership-based authorization added to surveys, appointments, leads
- [2026-02-11] Admin role check added for system settings
- [2026-02-11] Server security hardening (ports changed, Docker isolation, ARI restricted)
- [2026-02-08] Complete platform overhaul: security, ViciDial autodialer, dual provider, universal tool registry
