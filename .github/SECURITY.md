# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| main    | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email: **security@speakmaxi.com**
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix**: Within 30 days for critical issues

## Security Measures

This project implements:
- Input validation on all API endpoints (Pydantic + Zod)
- Parameterized database queries (SQLAlchemy ORM)
- JWT-based authentication with token rotation
- Ownership-based authorization
- CORS restrictions
- Rate limiting
- Structured logging for audit trails
- Secret scanning prevention
- Docker security (no-new-privileges, resource limits)
