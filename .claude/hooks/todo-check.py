#!/usr/bin/env python3
"""Stop hook: warn if TODO/FIXME comments exist in recently changed files."""
import json
import subprocess
import sys


def scan_todos_in_changed_files():
    """Find TODO/FIXME comments in recently modified files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AM"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return []

        todos = []
        for f in result.stdout.strip().splitlines():
            if not f or not f.endswith((".py", ".ts", ".tsx", ".js")):
                continue
            grep = subprocess.run(
                ["grep", "-n", "-E", r"TODO|FIXME|HACK|XXX", f],
                capture_output=True, text=True, timeout=5,
            )
            if grep.stdout.strip():
                for line in grep.stdout.strip().splitlines()[:3]:
                    todos.append(f"{f}:{line.strip()}")
        return todos
    except Exception:
        return []


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        data = {}

    stop_reason = data.get("stop_reason", "end_turn")
    if stop_reason != "end_turn":
        sys.exit(0)

    todos = scan_todos_in_changed_files()
    if todos:
        msg = f"Found {len(todos)} TODO/FIXME in changed files:\n"
        for t in todos[:5]:
            msg += f"  - {t}\n"
        msg += "Consider creating GitHub issues: /todo-scan"
        print(json.dumps({"warning": msg}))

    sys.exit(0)


if __name__ == "__main__":
    main()
