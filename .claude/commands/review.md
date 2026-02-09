# /review - Code Review

Review the specified file or recent git changes.

## Checklist
1. **Security**: Injection risks, hardcoded secrets, input validation gaps
2. **Performance**: N+1 queries, unnecessary loops, missing caching opportunities
3. **Error Handling**: Uncaught exceptions, missing error propagation, silent failures
4. **Type Safety**: Missing types, unsafe casts, implicit `any`
5. **Code Quality**: DRY violations, dead code, magic values, unclear naming
6. **Architecture**: Coupling, responsibility leaks, dependency issues

## Process
1. If no file specified → run `get_changed_files` and review git diff
2. Read target file(s) completely
3. Run `get_errors` for existing diagnostics
4. Apply checklist

## Output
For each issue:
- **Severity**: 🔴 Critical | 🟡 Warning | 🔵 Info
- **Location**: File + line link
- **Issue**: What's wrong
- **Fix**: Concrete recommendation with code if helpful
