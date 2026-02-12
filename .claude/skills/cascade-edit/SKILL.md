---
description: After making a change, find all related locations that need updating (like Copilot Next Edit Suggestions)
---

# /cascade-edit - Cascading Edit Detection

After a change, find all related code locations that may need updating.

## Process
1. Get recent changes: `!git diff --unified=0 HEAD`
2. If no staged diff, get unstaged: `!git diff --unified=0`
3. Identify changed symbols: function names, variable names, types, parameters, imports
4. For each changed symbol, search the entire codebase for all references using Grep
5. For each reference found, determine if it needs updating due to the original change
6. Present a numbered list of suggested cascading edits with file:line

## Detection Patterns
- **Renamed function/variable**: Find all call sites and references
- **Changed function signature**: Find all callers, update arguments
- **Changed type/interface/schema**: Find all serializers, validators, tests using that type
- **Changed API endpoint path**: Find all frontend fetch calls, API docs, tests
- **Changed Pydantic model field**: Find all places reading/writing that field
- **Changed environment variable name**: Find all config references, docker-compose, deployment files
- **Changed database column**: Find all queries, migrations, serializers referencing it

## Output Format
For each suggested edit:
- **File**: path:line
- **Symbol**: what needs changing
- **Reason**: why it needs to change (e.g., "calls renamed function X")
- **Suggested Fix**: concrete code change

## Rules
- Only suggest changes that are directly related to the original edit
- Group suggestions by file for efficient editing
- Mark each suggestion as REQUIRED (will break) or RECOMMENDED (consistency)
