#!/usr/bin/env python3
"""PreToolUse hook: block dangerous bash commands."""
import json
import sys


BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "DROP DATABASE",
    "DROP TABLE",
    "TRUNCATE",
    "--no-verify",
    "force-push",
    "push --force",
    "reset --hard",
]


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in command.lower():
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": f"Blocked: command contains '{pattern}'",
                        }
                    }
                )
            )
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
