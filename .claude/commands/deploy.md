# /deploy - Pre-Deployment Check

Verify the project is ready for deployment.

## Checks (auto-detect what applies)
1. **Build** — Can the project build without errors?
   - Python: `python -m py_compile` on main entry
   - Node/TS: `npm run build` or `npx tsc --noEmit`
   - Docker: Validate Dockerfile(s) and docker-compose syntax
2. **Environment** — Are all required env vars documented?
   - Compare `.env.example` vs actual config usage
   - Flag any hardcoded localhost/dev URLs
3. **Dependencies** — Are lock files up to date?
   - `requirements.txt` / `poetry.lock` / `package-lock.json` / `pnpm-lock.yaml`
4. **Database** — Any pending migrations or schema scripts?
5. **Security** — Debug mode off? CORS restrictive? Secrets in env vars?
6. **Tests** — Do tests pass? (if test infra exists)

## Output
- ✅ Ready / ❌ Blocked / ⚠️ Warning for each check
- Final go/no-go summary
