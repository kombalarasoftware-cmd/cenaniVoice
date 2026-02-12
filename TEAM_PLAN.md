# VoiceAI Platform — Team & Task Distribution Plan

> Last updated: 2026-02-11
> Based on full code review findings

---

## 🏗️ Team Roles

### 1. Backend Lead (Security & Architecture)
**Focus:** API security, authentication, authorization, architecture patterns

**Responsibilities:**
- Owner-based access control across all endpoints
- Authentication/authorization fixes
- Rate limiting & input validation
- Database session management (async/sync patterns)
- API route conflict resolution

### 2. Backend Developer (Services & Integration)
**Focus:** Business logic, external service integrations, call flow

**Responsibilities:**
- Asterisk ARI/Bridge service improvements
- OpenAI Realtime & Ultravox provider maintenance
- Redis connection pooling
- Celery task reliability
- Tool registry & call provider factory
- Prompt builder consolidation (DRY)

### 3. Frontend Developer
**Focus:** Next.js UI, state management, API integration

**Responsibilities:**
- Server-side auth middleware (JWT validation)
- Token refresh mechanism
- Type-safe API client
- Real-time call dashboard (SSE/WebSocket)
- UI components & design system

### 4. DevOps / Infrastructure
**Focus:** Docker, Asterisk config, CI/CD, security hardening

**Responsibilities:**
- Asterisk credential management (envsubst / entrypoint script)
- Docker Compose optimization
- TLS/SSL setup
- Missing Asterisk configs (modules.conf, logger.conf, etc.)
- Alembic migration strategy
- Monitoring & logging

---

## 📋 Sprint Backlog — Priority Order

### Sprint 1: Security Hardening (Critical)

| # | Task | Role | Est. | Status |
|---|------|------|------|--------|
| S1-01 | Add owner_id filtering to appointments, leads, surveys, documents, dial_lists, knowledge_base endpoints | Backend Lead | 4h | ⬜ TODO |
| S1-02 | Add auth dependency to prompt_generator.py | Backend Lead | 1h | ⬜ TODO |
| S1-03 | Add auth to numbers.py `/validate` endpoint | Backend Lead | 30m | ⬜ TODO |
| S1-04 | Fix Asterisk hardcoded credentials — implement entrypoint envsubst | DevOps | 3h | ⬜ TODO |
| S1-05 | Remove credentials from Dockerfile HEALTHCHECK | DevOps | 30m | ⬜ TODO |
| S1-06 | Restrict ARI CORS (`allowed_origins`) | DevOps | 30m | ⬜ TODO |
| S1-07 | Encrypt SIP trunk passwords in DB | Backend Lead | 2h | ⬜ TODO |
| S1-08 | Rename `get_current_user_optional` → `get_current_user` or make truly optional | Backend Lead | 1h | ⬜ TODO |

### Sprint 2: Bug Fixes (High)

| # | Task | Role | Est. | Status |
|---|------|------|------|--------|
| S2-01 | Fix route conflicts: recordings.py duplicate download, surveys agent/summary, calls tags/available | Backend Lead | 2h | ⬜ TODO |
| S2-02 | Fix caller_id bug in campaigns.py and openai_provider.py (using callee number instead of caller) | Backend Dev | 1h | ⬜ TODO |
| S2-03 | Fix appointments.py recursive call bug in `update_appointment` | Backend Lead | 30m | ⬜ TODO |
| S2-04 | Fix Redis connection pooling in asterisk_bridge.py (create shared pool) | Backend Dev | 3h | ⬜ TODO |
| S2-05 | Fix sync Redis client in openai_provider.py & ultravox_provider.py (use async) | Backend Dev | 2h | ⬜ TODO |
| S2-06 | Fix campaigns.py async DB session race condition in background tasks | Backend Dev | 2h | ⬜ TODO |
| S2-07 | Fix celery_tasks.py `asyncio.run()` — use `async_to_sync` pattern | Backend Dev | 2h | ⬜ TODO |
| S2-08 | Fix outbound_calls.py — return proper HTTP status codes on errors | Backend Lead | 1h | ⬜ TODO |
| S2-09 | Fix `_normalize_phone` — add `+` prefix with country code | Backend Dev | 30m | ⬜ TODO |

### Sprint 3: Data Integrity & Performance (Medium)

| # | Task | Role | Est. | Status |
|---|------|------|------|--------|
| S3-01 | Create proper Alembic migrations for all 18 base tables | Backend Lead | 6h | ⬜ TODO |
| S3-02 | Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` across all models | Backend Dev | 2h | ⬜ TODO |
| S3-03 | Fix N+1 queries in appointments, leads, surveys — use `joinedload` | Backend Dev | 2h | ⬜ TODO |
| S3-04 | Add missing model/enum exports to `models/__init__.py` (20 items) | Backend Dev | 1h | ⬜ TODO |
| S3-05 | Consolidate duplicate prompt builders (openai_realtime + ultravox_provider) | Backend Dev | 3h | ✅ DONE |
| S3-06 | Add `httpx.AsyncClient` connection pooling (document_service, ultravox_service) | Backend Dev | 2h | ⬜ TODO |
| S3-07 | Add duplicate agent — copy missing fields (timezone, smart_features, survey_config) | Backend Dev | 30m | ⬜ TODO |

### Sprint 4: Infrastructure (Medium)

| # | Task | Role | Est. | Status |
|---|------|------|------|--------|
| S4-01 | Create missing Asterisk configs: modules.conf, logger.conf, asterisk.conf, musiconhold.conf | DevOps | 3h | ⬜ TODO |
| S4-02 | Enable TLS for ARI and SIP trunk | DevOps | 4h | ⬜ TODO |
| S4-03 | Move circuit breaker state from in-memory to Redis | Backend Dev | 2h | ⬜ TODO |
| S4-04 | Expand RTP port range (10000-10200 for 100 concurrent calls) | DevOps | 30m | ⬜ TODO |
| S4-05 | Remove hardcoded IPs from pjsip.conf — use env variables | DevOps | 1h | ⬜ TODO |

### Sprint 5: Frontend Improvements (Medium)

| # | Task | Role | Est. | Status |
|---|------|------|------|--------|
| S5-01 | Implement server-side JWT validation middleware | Frontend Dev | 3h | ⬜ TODO |
| S5-02 | Add token refresh mechanism | Frontend Dev | 2h | ⬜ TODO |
| S5-03 | Type-safe API client with proper generics | Frontend Dev | 3h | ⬜ TODO |
| S5-04 | Fix api.ts — don't set Content-Type for FormData uploads | Frontend Dev | 30m | ⬜ TODO |
| S5-05 | Replace hardcoded localhost fallback with required env variable | Frontend Dev | 30m | ⬜ TODO |

### Sprint 6: Refactoring & Cleanup (Low)

| # | Task | Role | Est. | Status |
|---|------|------|------|--------|
| S6-01 | Refactor Agent model — extract prompt fields to separate table | Backend Lead | 6h | ⬜ TODO |
| S6-02 | Add DocumentChunk.embedding column via migration (pgvector) | Backend Dev | 2h | ⬜ TODO |
| S6-03 | Remove dead code: `handle_call_complete` in celery_tasks.py | Backend Dev | 30m | ⬜ TODO |
| S6-04 | Remove unused imports (BeautifulSoup in audio_bridge.py, etc.) | Backend Dev | 1h | ⬜ TODO |
| S6-05 | Remove hardcoded fallback prompt from asterisk_bridge.py | Backend Dev | 1h | ⬜ TODO |
| S6-06 | Fix `settings` variable shadowing in settings.py | Backend Lead | 30m | ⬜ TODO |
| S6-07 | Implement real SIP trunk connection test (currently returns fake data) | Backend Dev | 2h | ⬜ TODO |
| S6-08 | Add proper error handling for Asterisk ARI callbacks (async/sync) | Backend Dev | 2h | ⬜ TODO |

---

## 📊 Summary

| Sprint | Tasks | Est. Total | Priority |
|--------|-------|-----------|----------|
| Sprint 1: Security | 8 | ~12h | 🔴 Critical |
| Sprint 2: Bug Fixes | 9 | ~14h | 🟠 High |
| Sprint 3: Data & Perf | 7 | ~16.5h | 🟡 Medium |
| Sprint 4: Infrastructure | 5 | ~10.5h | 🟡 Medium |
| Sprint 5: Frontend | 5 | ~9h | 🟡 Medium |
| Sprint 6: Refactoring | 8 | ~15h | 🔵 Low |
| **Total** | **42** | **~77h** | — |

---

## 🔑 Key Decisions Needed

1. **Auth strategy:** Keep `get_current_user_optional` or switch to strict `get_current_user` everywhere?
2. **Migration strategy:** Reset all migrations (single initial) or create incremental patches?
3. **Agent model:** Keep monolithic or split prompt fields to separate table?
4. **Redis pattern:** Single shared pool or per-service pools?
5. **Asterisk credentials:** envsubst in entrypoint or template generation?
