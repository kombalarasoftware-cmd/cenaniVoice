# /test - Test Generation

Generate comprehensive tests for the specified file or module.

## Process
1. Read the target file completely
2. Identify all public functions, methods, classes
3. Detect the project's test framework (pytest / vitest / jest / mocha)
4. Generate tests matching existing patterns if tests exist, else use defaults

## Test Categories
- **Happy Path** — Normal expected behavior
- **Edge Cases** — Empty/null/max/min/boundary inputs
- **Error Cases** — Invalid inputs, failures, timeouts
- **Integration** — Component interactions (if applicable)

## Language-Specific Defaults

**Python**: pytest + pytest-asyncio, unittest.mock, place in `tests/` mirroring source
**TypeScript/JavaScript**: vitest or jest, @testing-library for React, place in `__tests__/` or `.test.ts`
**Go**: standard testing package, place in same package as `_test.go`

## Rules
- Target ≥80% coverage of the target file
- Mock external dependencies (DB, API, filesystem)
- Descriptive names: `test_should_return_error_when_input_empty`
- One assertion focus per test
- Arrange → Act → Assert pattern
- No order-dependent tests
