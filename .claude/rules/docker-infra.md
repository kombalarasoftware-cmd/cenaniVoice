---
paths:
  - "docker-compose*.yml"
  - "Dockerfile*"
  - "nginx/**/*"
  - "asterisk/**/*"
  - ".env.example"
---

# Docker & Infrastructure Rules

- Never expose internal service ports in production compose
- Use multi-stage builds for smaller images
- Run containers as non-root user where possible
- Health checks required on all services
- Restart policy: unless-stopped for production
- Entrypoint scripts must use LF line endings (not CRLF)
- Asterisk config: use environment variable substitution for IPs
- Nginx: SSL termination, rate limiting, security headers
- MinIO buckets must be pre-created in entrypoint
- Use .env.example as template, never commit actual .env files
