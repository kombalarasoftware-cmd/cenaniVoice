#!/usr/bin/env python3
"""Status line script: shows model, context usage, cost, and git branch."""
import json
import subprocess
import sys


def get_git_branch():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print("")
        return

    model = data.get("model", {}).get("display_name", "?")
    ctx = data.get("context_window", {})
    used_pct = ctx.get("used_percentage", 0)
    cost = data.get("cost", {}).get("total_cost_usd", 0)
    lines_added = data.get("cost", {}).get("total_lines_added", 0)
    lines_removed = data.get("cost", {}).get("total_lines_removed", 0)

    branch = get_git_branch()

    # Build status parts
    parts = [f"\033[36m{model}\033[0m"]

    if branch:
        parts.append(f"\033[33m{branch}\033[0m")

    # Context bar with color coding
    if used_pct > 80:
        ctx_color = "\033[31m"  # red
    elif used_pct > 60:
        ctx_color = "\033[33m"  # yellow
    else:
        ctx_color = "\033[32m"  # green
    parts.append(f"ctx:{ctx_color}{used_pct:.0f}%\033[0m")

    if cost > 0:
        parts.append(f"${cost:.2f}")

    if lines_added or lines_removed:
        parts.append(f"\033[32m+{lines_added}\033[0m/\033[31m-{lines_removed}\033[0m")

    print(" | ".join(parts))


if __name__ == "__main__":
    main()
