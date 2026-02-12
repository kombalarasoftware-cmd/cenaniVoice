#!/usr/bin/env python3
"""PostToolUse hook: run ruff linter on edited Python files (async)."""
import json
import os
import subprocess
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path.endswith(".py"):
        sys.exit(0)

    # Check if ruff is available
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", file_path, "--output-format", "text"],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        sys.exit(0)

    if result.stdout.strip():
        lines = result.stdout.strip().splitlines()
        error_count = len(lines)
        preview = "\n".join(lines[:5])
        if error_count > 5:
            preview += f"\n  ... and {error_count - 5} more"
        print(f"Ruff: {error_count} issues in {os.path.basename(file_path)}:\n{preview}")

    sys.exit(0)


if __name__ == "__main__":
    main()
