---
paths:
  - "backend/tasks/**/*.py"
  - "backend/app/tasks/**/*.py"
---

# Celery Task Rules
- Always set task_id for idempotency
- Set max_retries and retry_backoff on all tasks
- Log task start and completion with structlog
- Use atomic DB operations (no ORM bulk updates without locks)
- Never access request context inside tasks
- Use bind=True for access to self (retry, request info)
- Handle task timeout gracefully with soft_time_limit
