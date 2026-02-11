---
description: Pre-deployment readiness check for the VoiceAI platform
allowed-tools: Read, Bash, Glob, Grep
---

# /deploy - Pre-Deployment Check

Verify the project is ready for deployment.

## Checks
1. **Build** — Can the project build without errors?
   - Backend: `python -m py_compile` on main entry
   - Frontend: `npm run build`
   - Docker: Validate docker-compose syntax
2. **Environment** — Are all required env vars documented?
   - Compare `.env.example` vs config.py Settings usage
   - Flag any hardcoded localhost/dev URLs
3. **Dependencies** — Are lock files up to date?
   - `requirements.txt` / `package-lock.json`
4. **Database** — Any pending Alembic migrations?
5. **Security** — Debug mode off? CORS restrictive? Secrets in env vars only?
6. **Tests** — Do tests pass? (`pytest` / `npm test`)

## Output
- PASS / FAIL / WARNING for each check
- Final go/no-go summary
