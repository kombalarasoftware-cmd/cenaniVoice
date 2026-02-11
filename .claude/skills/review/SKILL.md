---
description: Code review with security, performance, and quality checks
allowed-tools: Read, Grep, Glob, Bash
---

# /review - Code Review

Review the specified file or recent git changes: $ARGUMENTS

## Current Changes
`!git diff --stat`

## Checklist
1. **Security**: Injection risks, hardcoded secrets, input validation gaps
2. **Performance**: N+1 queries, unnecessary loops, missing caching opportunities
3. **Error Handling**: Uncaught exceptions, missing error propagation, silent failures
4. **Type Safety**: Missing types, unsafe casts, implicit `any`
5. **Code Quality**: DRY violations, dead code, magic values, unclear naming
6. **Architecture**: Coupling, responsibility leaks, dependency issues

## Process
1. If no file specified → run `git diff` to review recent changes
2. Read target file(s) completely
3. Check for IDE diagnostics if available
4. Apply checklist above

## Output
For each issue:
- **Severity**: CRITICAL | WARNING | INFO
- **Location**: File + line number
- **Issue**: What's wrong
- **Fix**: Concrete recommendation with code if helpful
