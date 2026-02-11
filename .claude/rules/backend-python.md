---
paths:
  - "backend/**/*.py"
---

# Python Backend Rules

- Use async/await for all database operations and external API calls
- Type hints required on all function signatures
- Use Pydantic models for request/response validation
- Use SQLAlchemy async session for database access
- Business logic goes in `app/services/`, not in route handlers
- Use `structlog` for structured JSON logging with request ID
- Use `app/core/config.py` Settings for all configuration (never hardcode)
- Alembic for all database schema changes (never raw ALTER TABLE)
- Use dependency injection via FastAPI Depends()
- Rate limiting via middleware, not per-endpoint
