---
applyTo: "**/*.py"
---

# Python Code Instructions

- Use Python 3.11+ features (type hints, match statements, StrEnum)
- All database operations must be async with AsyncSession
- Use SQLAlchemy 2.0 query syntax (select, where) not legacy Query API
- Use Pydantic v2 for all request/response models
- Use structlog.get_logger() for logging, never print() or logging.getLogger()
- All API endpoints must have Pydantic request/response models
- Use FastAPI dependency injection with Depends() for auth, db sessions, and services
- Error handling: catch specific exceptions, log with structlog, return appropriate HTTP status
- Imports: stdlib first, then third-party, then local, separated by blank lines
- Use async def for all endpoint handlers and service methods that do I/O
