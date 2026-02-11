#!/usr/bin/env python3
"""SessionStart hook: verify environment and display project status."""
import json
import os
import subprocess
import sys


def check_git_status():
    """Get current branch and dirty file count."""
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        branch_name = branch.stdout.strip() if branch.returncode == 0 else "unknown"
        dirty_count = len(status.stdout.strip().splitlines()) if status.stdout.strip() else 0
        return branch_name, dirty_count
    except Exception:
        return "unknown", 0


def check_env_file():
    """Check if .env.prod exists (required for production)."""
    return os.path.exists(".env.prod") or os.path.exists(".env")


def main():
    branch, dirty = check_git_status()
    has_env = check_env_file()

    warnings = []
    if dirty > 0:
        warnings.append(f"{dirty} uncommitted file(s)")
    if not has_env:
        warnings.append("No .env file found")

    status = "ready" if not warnings else "warnings"
    summary = f"Branch: {branch}"
    if warnings:
        summary += f" | Warnings: {', '.join(warnings)}"

    # Output status for Claude to see
    print(json.dumps({
        "branch": branch,
        "dirty_files": dirty,
        "has_env": has_env,
        "status": status,
        "summary": summary,
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
