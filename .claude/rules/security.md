---
paths:
  - "backend/app/api/**/*.py"
  - "backend/app/services/**/*.py"
  - "frontend/src/**/*.{ts,tsx}"
---

# Security Rules

- All API endpoints must have authentication (get_current_user dependency)
- Role-based access: check user.role before sensitive operations
- Input validation: Pydantic on backend, Zod on frontend
- SQL: always use SQLAlchemy ORM or parameterized queries
- File uploads: validate type, size, and sanitize filename
- CORS: explicit origins list, never wildcard in production
- Passwords: bcrypt only, never store or log plaintext
- JWT: validate expiration, use short-lived tokens
- Secrets: environment variables via Settings, never in code
