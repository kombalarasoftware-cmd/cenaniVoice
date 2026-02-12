# VoiceAI Platform - Copilot Instructions

## Project Overview
AI-powered outbound/inbound voice call platform with dual provider support (OpenAI Realtime + Ultravox). Manages concurrent voice calls through Asterisk PBX with real-time AI conversation capabilities.

## Tech Stack
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, React Query v5, Zod validation
- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Celery + Beat, structlog, Alembic
- **Infrastructure**: PostgreSQL 16 (pgvector), Redis 7, Asterisk 20 PBX, MinIO, Nginx, Docker Compose
- **AI Providers**: OpenAI Realtime API (WebSocket), Ultravox REST API

## Project Structure
```
backend/
  api/v1/endpoints/    # FastAPI route handlers
  services/            # Business logic layer
  models/              # SQLAlchemy ORM models
  core/                # Config, security, dependencies
  tasks/               # Celery async tasks
  alembic/             # Database migrations
frontend/
  app/                 # Next.js 14 App Router pages
  components/          # React components (shadcn/ui based)
  lib/                 # API client, utilities, types
asterisk/              # Asterisk PBX configuration
nginx/                 # Reverse proxy configuration
```

## Build and Development Commands
```bash
# Start all services
docker compose up -d

# Backend development
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend development
cd frontend && npm ci
npm run dev        # Development server on :3000
npm run build      # Production build
npm run lint       # ESLint check

# Database migrations
cd backend && alembic upgrade head
alembic revision --autogenerate -m "description"

# Tests
cd backend && python -m pytest -v --tb=short
cd frontend && npm run test
```

## Code Standards

### Language Policy
- ALL code, comments, docstrings, API descriptions, UI text, and log messages MUST be in English
- No Turkish anywhere in the codebase
- AI agent spoken language is controlled by the language setting, not instruction language

### TypeScript (Frontend)
- Never use any type, use explicit types or unknown
- Use explicit return types on all functions
- Use early return pattern to reduce nesting
- Validate inputs with Zod schemas
- Use React Query v5 for server state management
- Components use shadcn/ui primitives

### Python (Backend)
- Use async/await for all database and HTTP operations
- SQLAlchemy 2.0 async style with AsyncSession
- Use Pydantic v2 models for request/response validation
- Structured logging with structlog (never use print)
- Use dependency injection via FastAPI Depends

### Security Rules
- No hardcoded secrets, use environment variables
- Parameterized queries only, no SQL string concatenation
- No eval or exec, ever
- Input validation on all API endpoints with Pydantic
- Ownership-based authorization on all data access
- CORS restricted to specific origins

## Architecture Patterns

### Dual AI Provider (Provider Factory)
Use ProviderFactory in backend/services/provider_factory.py to get the correct AI provider.
Provider is selected per-agent: openai or ultravox.

### Universal Tool Registry
All AI tools are registered through backend/services/tool_registry.py.
Tools are provider-agnostic and converted at runtime.

### ViciDial-Style Hopper
Leads are loaded into a hopper table for fast sequential access.
Use atomic SQL increments for concurrent call distribution.

### Circuit Breaker
External API calls use circuit breaker pattern.
States: CLOSED then OPEN then HALF_OPEN. In-memory state resets on restart.

## Services and Ports
| Service | Port | Notes |
|---------|------|-------|
| Frontend | 3000 | Next.js dev server |
| Backend | 8000 | FastAPI with Swagger at /api/docs |
| PostgreSQL | 5432 | Internal only in production |
| Redis | 6379 | Internal only in production |
| Asterisk | 5043 | SIP over TCP |
| MinIO | 9000/9001 | Object storage |

## Shell Compatibility (Windows)
This project runs on Windows. The VS Code terminal is configured to use **Git Bash**.
- **NEVER use bash heredoc** (`<<EOF`) syntax — it fails in PowerShell and may fail in some Git Bash contexts
- For multi-line git commits, use the `-m` flag multiple times:
  ```bash
  git commit -m "feat: add new feature" -m "Detailed description here" -m "Co-Authored-By: ..."
  ```
- For `gh pr create`, use `--body` with a simple string (no heredoc):
  ```bash
  gh pr create --title "Add feature" --body "## Summary
  - Change 1
  - Change 2"
  ```
- Prefer simple single-line commands over complex piped/heredoc constructs
- Use `git commit -F <file>` for complex commit messages (write to temp file first)

## Common Gotchas
- SIP passwords must match between Asterisk config and database
- AudioSocket requires raw PCM 16-bit, 16kHz, mono codec
- Circuit breaker state is in-memory and resets on restart
- MinIO buckets must be pre-created before use
- Frontend uses relative API URLs (no hardcoded localhost)
- Shell scripts and Docker entrypoints require LF line endings
- pgvector extension must be enabled in PostgreSQL
- **PowerShell does not support bash heredoc** — use Git Bash or alternative syntax (see above)
