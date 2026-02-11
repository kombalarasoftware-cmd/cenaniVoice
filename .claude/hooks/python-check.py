#!/usr/bin/env python3
"""PostToolUse hook: verify Python syntax after Write/Edit operations."""
import json
import sys
import subprocess


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        sys.exit(0)

    result = subprocess.run(
        [sys.executable, "-m", "py_compile", file_path],
        capture_output=True,
        text=True,
        timeout=15,
    )

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip()
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": f"Python syntax error in {file_path}: {error_msg}",
                }
            )
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
