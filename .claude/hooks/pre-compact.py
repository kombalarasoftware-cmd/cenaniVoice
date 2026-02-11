#!/usr/bin/env python3
"""PreCompact hook: preserve critical context before conversation compaction."""
import json
import subprocess
import sys


def get_modified_files():
    """Get list of files modified in this session."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip().splitlines()
        return []
    except Exception:
        return []


def get_recent_commits(count=5):
    """Get recent commit messages."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--oneline"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except Exception:
        return ""


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        data = {}

    modified = get_modified_files()
    commits = get_recent_commits()

    # Build context preservation instructions
    preserve = []

    if modified:
        preserve.append(f"Modified files in this session: {', '.join(modified)}")

    if commits:
        preserve.append(f"Recent commits:\n{commits}")

    preserve.append("Preserve: all architecture decisions, error resolutions, and test results")
    preserve.append("Preserve: file paths and line numbers of all changes made")

    if preserve:
        print(json.dumps({
            "instructions": "\n".join(preserve)
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
