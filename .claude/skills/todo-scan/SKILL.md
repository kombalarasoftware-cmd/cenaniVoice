---
description: Scan codebase for TODO/FIXME comments and create GitHub issues (like Copilot TODO detection)
---

# /todo-scan - TODO Detection and Issue Creator

Scan for TODO/FIXME/HACK comments and optionally create GitHub issues.

## Process
1. Scan backend: Use Grep for pattern `TODO|FIXME|HACK|XXX` in `backend/` with `*.py` filter
2. Scan frontend: Use Grep for pattern `TODO|FIXME|HACK|XXX` in `frontend/` with `*.ts,*.tsx` filter
3. Scan infra: Use Grep for pattern `TODO|FIXME|HACK|XXX` in docker-compose.yml, Dockerfile, nginx/, asterisk/
4. For each found item:
   - Read 5 lines of surrounding context
   - Categorize: bug, feature, tech-debt, security, performance
   - Estimate priority: P0 (blocking), P1 (important), P2 (nice-to-have)
5. Present a numbered summary table
6. Ask user which items to convert to GitHub issues
7. For approved items, create issues via `gh issue create`

## Issue Template
```
Title: [Category] Description from TODO context
Labels: auto-assigned (bug/enhancement/tech-debt + backend/frontend/infrastructure)

Body:
## Source
`file:line` — found in [function/class name]

## TODO Comment
> exact text of the comment

## Context
\`\`\`language
surrounding code snippet (5 lines)
\`\`\`

## Suggested Action
What needs to be done based on the context

## Priority
P0/P1/P2 with justification
```

## Rules
- Group TODOs by file and category
- Skip TODOs in node_modules, __pycache__, .venv, migrations
- Flag any TODO older than 30 days (check git blame)
- After creating issues, suggest removing the TODO comment and adding issue reference
