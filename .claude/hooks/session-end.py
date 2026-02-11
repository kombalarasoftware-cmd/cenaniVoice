#!/usr/bin/env python3
"""SessionEnd hook: cleanup and session summary on exit."""
import json
import subprocess
import sys
from datetime import datetime


def get_session_stats():
    """Gather session statistics."""
    stats = {}

    # Check for uncommitted changes
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            changes = result.stdout.strip().splitlines()
            stats["uncommitted_files"] = len(changes)
            if changes:
                stats["files"] = [line.strip() for line in changes[:10]]
    except Exception:
        pass

    # Check for staged changes
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            stats["staged_changes"] = result.stdout.strip().splitlines()[-1]
    except Exception:
        pass

    return stats


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        data = {}

    stats = get_session_stats()

    # Warn about uncommitted changes
    uncommitted = stats.get("uncommitted_files", 0)
    if uncommitted > 0:
        files = stats.get("files", [])
        print(json.dumps({
            "warning": f"{uncommitted} uncommitted file(s) remaining",
            "files": files,
            "timestamp": datetime.now().isoformat()
        }))

    sys.exit(0)


if __name__ == "__main__":
    main()
