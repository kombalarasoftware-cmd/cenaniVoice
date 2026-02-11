---
description: Generate comprehensive tests for a file or module
allowed-tools: Read, Write, Bash, Glob, Grep
---

# /test - Test Generation

Generate tests for the specified target: $ARGUMENTS

## Process
1. Read the target file completely
2. Identify all public functions, methods, classes
3. Detect framework: pytest (backend) or vitest/jest (frontend)
4. Generate tests matching existing patterns

## Test Categories
- **Happy Path** — Normal expected behavior
- **Edge Cases** — Empty/null/max/min/boundary inputs
- **Error Cases** — Invalid inputs, failures, timeouts
- **Integration** — Component interactions (if applicable)

## Defaults
- **Python**: pytest + pytest-asyncio, unittest.mock, place in `tests/` mirroring source
- **TypeScript**: vitest or jest, @testing-library for React, place in `__tests__/` or `.test.ts`

## Rules
- Target 80%+ coverage of the target file
- Mock external dependencies (DB, API, filesystem)
- Descriptive names: `test_should_return_error_when_input_empty`
- One assertion focus per test
- Arrange / Act / Assert pattern
- No order-dependent tests
