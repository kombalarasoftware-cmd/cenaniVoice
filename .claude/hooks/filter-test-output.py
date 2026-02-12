#!/usr/bin/env python3
"""PreToolUse hook: filter test output to show only failures, saving tokens."""
import json
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Check if this is a test command
    test_patterns = [
        r"^python -m pytest",
        r"^pytest",
        r"^npm run test",
        r"^npm test",
        r"^npx jest",
        r"^npx vitest",
    ]

    is_test = any(re.match(p, command.strip()) for p in test_patterns)

    if is_test:
        # Append grep to filter only failures and limit output
        filtered = f'{command} 2>&1 | grep -A 5 -E "(FAIL|ERROR|error:|FAILED|assert|Exception|Traceback)" | head -100'
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": {
                    "command": filtered
                }
            }
        }))
    else:
        print("{}")

    sys.exit(0)


if __name__ == "__main__":
    main()
