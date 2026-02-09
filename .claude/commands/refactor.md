# /refactor - Code Refactoring

Analyze and restructure code for better maintainability.

## Analysis
1. Read the entire target file/module
2. Map dependencies with `list_code_usages`
3. Identify smells:
   - Functions > 50 lines
   - Classes > 300 lines
   - Deep nesting > 3 levels
   - Duplicated logic
   - Long parameter lists (> 4 params)
   - God objects

## Strategies
- **Extract Function/Method** — Break large blocks into focused units
- **Extract Class/Module** — Split by responsibility
- **Introduce Parameter Object** — Group related params
- **Replace Conditional with Polymorphism** — Simplify branching
- **Early Return** — Flatten nested conditions

## Rules
- Incremental, commit-ready changes
- Maintain backward compatibility unless asked otherwise
- Update ALL callers when signatures change (use `list_code_usages`)
- Add/improve type annotations
- No behavior changes — structural only
- Run `get_errors` after each change

## Output
- Before/after summary
- All modified files listed
- Risk assessment per change
