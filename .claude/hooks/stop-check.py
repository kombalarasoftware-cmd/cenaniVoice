#!/usr/bin/env python3
"""Stop hook: verify no obvious issues before Claude finishes its response."""
import json
import subprocess
import sys


def check_syntax_errors():
    """Quick check for any Python files with syntax errors in recent changes."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AM"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return []

        errors = []
        for f in result.stdout.strip().splitlines():
            if f.endswith(".py"):
                check = subprocess.run(
                    [sys.executable, "-m", "py_compile", f],
                    capture_output=True, text=True, timeout=5,
                )
                if check.returncode != 0:
                    errors.append(f)
        return errors
    except Exception:
        return []


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        data = {}

    # Prevent infinite loop: if already in a stop hook cycle, exit immediately
    if data.get("stop_hook_active"):
        sys.exit(0)

    stop_reason = data.get("stop_reason", "end_turn")

    # Only run checks on normal stop (not on tool use)
    if stop_reason != "end_turn":
        sys.exit(0)

    errors = check_syntax_errors()
    if errors:
        print(json.dumps({
            "warning": f"Syntax errors in modified files: {', '.join(errors)}",
            "files": errors,
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
