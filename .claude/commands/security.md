# /security - Security Audit

Scan for security vulnerabilities in the specified scope (file, module, or project).

## Scan Areas

### 1. Secrets & Credentials
- Hardcoded API keys, passwords, tokens, connection strings
- `.env` files tracked in git
- Secrets in Docker/compose files or CI configs
- Search: `password|secret|api_key|token|private_key|credential`

### 2. Injection Risks
- SQL injection (string formatting in queries, raw SQL)
- XSS (unescaped user input in HTML/JSX)
- Command injection (shell exec with user input)
- Path traversal (user input in file paths)

### 3. Auth & Access Control
- Missing auth checks on endpoints/routes
- Weak token generation or session management
- Missing RBAC/permission checks

### 4. Dependencies
- Known CVEs in installed packages
- Outdated packages with security patches
- `npm audit` / `pip-audit` results if available

### 5. Configuration
- Debug/dev mode in production configs
- Permissive CORS (`*`)
- Missing security headers
- Docker running as root
- Open ports/services

## Output
For each finding:
- **Severity**: 🔴 Critical | 🟡 Medium | 🟢 Low
- **Category**: Scan area
- **Location**: File + line
- **Issue**: What's vulnerable
- **Fix**: How to remediate
- **Reference**: CWE/OWASP if applicable
