---
description: Fix a GitHub issue by number
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
context: fork
---

# /fix-issue - Fix GitHub Issue

Fix the specified GitHub issue: $ARGUMENTS

## Process
1. Fetch issue details: `gh issue view $ARGUMENTS`
2. Read and understand the issue description and comments
3. Investigate the codebase to find relevant files
4. Implement the fix
5. Run tests to verify the fix
6. Create a commit with message referencing the issue: `fix: description (closes #N)`

## Rules
- Always reference the issue number in commit message
- Run existing tests after fixing
- If the fix requires new tests, create them
- If the issue is unclear, ask for clarification before coding
