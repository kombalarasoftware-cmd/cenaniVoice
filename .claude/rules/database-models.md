---
paths:
  - "backend/models/**/*.py"
  - "backend/app/models/**/*.py"
  - "backend/alembic/**/*.py"
---

# Database Model Rules
- All models must have created_at and updated_at timestamps
- Use UUID primary keys (not auto-increment integers)
- Add proper indexes on frequently queried columns
- Foreign keys must have ondelete behavior defined (CASCADE or SET NULL)
- Enum columns must use SQLAlchemy Enum with native_enum=False for portability
- Migration files must be reversible (include downgrade)
- Never modify existing migration files — create new ones
