---
paths:
  - "backend/api/**/*.py"
  - "backend/app/api/**/*.py"
---

# API Route Rules
- All routes must have authentication dependency (get_current_user)
- Use Pydantic response models on every endpoint
- Apply ownership filtering on all list/detail endpoints
- Add rate limiting via middleware for public endpoints
- Use HTTP status codes correctly: 201 for create, 204 for delete, 404 for not found
- Always return structured error responses with detail field
