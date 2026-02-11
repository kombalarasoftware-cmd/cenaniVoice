# VoiceAI Platform

AI-powered outbound/inbound voice call platform with dual provider support (OpenAI Realtime + Ultravox).

## Tech Stack
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
- **Backend**: FastAPI + SQLAlchemy (async) + Celery + structlog
- **Infrastructure**: PostgreSQL 16 (pgvector) + Redis 7 + Asterisk 20 + MinIO + Nginx
- **AI Providers**: OpenAI Realtime API (WebSocket) + Ultravox API (SIP-native)

## Build & Run Commands
```bash
# Development
docker compose up -d                    # Start all services
docker compose logs -f backend          # Follow backend logs

# Backend
cd backend && python -m pytest          # Run tests
python -m py_compile app/main.py        # Syntax check
alembic upgrade head                    # Run migrations

# Frontend
cd frontend && npm run build            # Production build
npm run lint                            # Lint check
npm run test                            # Run tests

# Production
docker compose -f docker-compose.prod.yml up -d
```

## Project Structure
```
backend/
  app/
    api/v1/       # Route handlers
    services/     # Business logic
    models/       # SQLAlchemy ORM models
    core/         # Config, database, security
    tasks/        # Celery background jobs
  alembic/        # Database migrations
frontend/
  src/
    app/          # Next.js App Router pages
    components/   # React components (ui, agents, call, dashboard)
    lib/          # API client, utilities
asterisk/         # SIP/PBX configuration
nginx/            # Reverse proxy + SSL
```

## Language Policy
- **No Turkish anywhere** in code — all UI text, comments, API descriptions, docstrings, log messages, and prompt instructions must be in English
- The AI agent's spoken language is controlled by the `language` setting, not by instruction language

## Key Architecture Decisions
- Dual AI provider with Provider Factory pattern (pluggable)
- ViciDial-style hopper system for campaign dialing
- Universal Tool Registry: single source, converts to OpenAI/Ultravox format
- Circuit breaker per provider (5 failures → 30s cooldown)
- Middleware order: RequestID → SecurityHeaders → BodySizeLimit → RateLimit → CORS

## Model Configuration
- Default: Sonnet (fast, cost-efficient)
- Planning: `--model opusplan` (Opus for plans, Sonnet for execution)
- Complex tasks: `--effort high`
- Quick lookups: `--effort low`

## Available Agents
- `security-reviewer` — OWASP-focused security audit (persistent memory)
- `code-reviewer` — Quality, performance, architecture review (persistent memory)
- `debugger` — Root cause analysis with project-specific patterns (persistent memory)
- `frontend-developer` — Next.js/React specialist (persistent memory)

## Available Skills
- `/review` — Code review with security + performance checks
- `/security` — OWASP-focused security vulnerability scan
- `/test` — Generate comprehensive tests
- `/deploy` — Pre-deployment readiness check
- `/refactor` — Analyze and restructure code (runs in fork context)
- `/changelog` — Generate changelog from git history
- `/fix-issue` — Fix a GitHub issue by number (runs in fork context)
- `/interview` — Interview user to gather requirements before implementing

## Plugins & Integrations
- **GitHub** — PR/issue management via MCP
- **Playwright** — Browser automation and visual testing
- **Context7** — Up-to-date library documentation
- **Sentry** — Error monitoring integration
- **Slack** — Task delegation from Slack
- **Figma** — Design-to-code integration
- **Pyright LSP** — Python type checking and code intelligence
- **TypeScript LSP** — TypeScript type checking and code intelligence

## Hook Events (8 active)
- **SessionStart** — Environment check on startup
- **PreToolUse** — Command validation before execution
- **PostToolUse** — Python syntax check after file edits (async)
- **Notification** — Windows toast notifications (async)
- **Stop** — Final verification before response ends
- **PreCompact** — Preserve critical context before compaction
- **SessionEnd** — Warn about uncommitted changes on exit (async)

## Agent SDK Scripts
Automation scripts in `.claude/scripts/`:
- `batch-migrate.sh` — Parallel file migration with `claude -p`
- `review-pr.sh` — Automated security + quality PR review
- `extract-api.sh` — Structured API endpoint extraction (JSON schema)

## Output Styles
Custom output style at `.claude/output-styles/engineering.md` — use `--output-style engineering`

## DevContainer
`.devcontainer/devcontainer.json` configured with Python 3.11, Node 18, PostgreSQL, Redis, gh CLI.

## References
@.claude/memory.md

## Compact Instructions
When context is compacted, preserve:
- Tech stack and build commands above
- Language policy (English only in code)
- Key architecture decisions
- All @import references
- The project rules from .claude/rules/ (backend-python, frontend-react, security, docker-infra)
