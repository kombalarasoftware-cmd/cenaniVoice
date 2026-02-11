---
description: Analyze and restructure code for better maintainability
---

# /refactor - Code Refactoring

Analyze and restructure the specified code: $ARGUMENTS

## Analysis
1. Read the entire target file/module
2. Map dependencies and usages
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
- **Early Return** — Flatten nested conditions

## Rules
- Incremental, commit-ready changes
- Maintain backward compatibility unless asked otherwise
- Update ALL callers when signatures change
- No behavior changes — structural only

## Output
- Before/after summary
- All modified files listed
- Risk assessment per change
