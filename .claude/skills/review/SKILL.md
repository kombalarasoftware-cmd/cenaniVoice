---
description: Code review with linter integration, security, performance, and quality checks (Copilot-style)
---

# /review - Code Review + Linter Integration

Review the specified file or recent git changes: $ARGUMENTS

## Step 1: Collect Linter Results
- Python files: `!python -m ruff check backend/ --output-format text 2>&1 | head -30`
- TypeScript files: `!cd frontend && npx eslint src/ --format stylish 2>&1 | head -30`
- Type check: `!cd frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

## Step 2: Current Changes
`!git diff --stat`

## Step 3: AI Review Checklist
1. **Linter Findings**: Address all ERROR level linter issues first
2. **Security**: Injection risks, hardcoded secrets, input validation gaps
3. **Performance**: N+1 queries, unnecessary loops, missing caching opportunities
4. **Error Handling**: Uncaught exceptions, missing error propagation, silent failures
5. **Type Safety**: Missing types, unsafe casts, implicit `any`
6. **Code Quality**: DRY violations, dead code, magic values, unclear naming
7. **Architecture**: Coupling, responsibility leaks, dependency issues
8. **Test Coverage**: Changed code has corresponding tests

## Process
1. Run linters first to collect automated findings
2. If no file specified, run `git diff` to review recent changes
3. Read target file(s) completely
4. Check for IDE diagnostics if available
5. Cross-reference linter results with AI analysis
6. Apply checklist above

## Output
For each issue:
- **Source**: LINTER | AI-REVIEW
- **Severity**: CRITICAL | WARNING | INFO
- **Location**: File + line number
- **Issue**: What's wrong
- **Fix**: Concrete recommendation with code if helpful

## Summary Table
At the end, provide a summary:
| Severity | Linter | AI Review | Total |
|----------|--------|-----------|-------|
| CRITICAL | N | N | N |
| WARNING  | N | N | N |
| INFO     | N | N | N |
