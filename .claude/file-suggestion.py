#!/usr/bin/env python3
"""File suggestion script: powers @ autocomplete with project-aware suggestions."""
import glob
import json
import os
import sys


# File extensions to prioritize
PRIORITY_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yml", ".yaml",
    ".md", ".sql", ".html", ".css", ".conf", ".env", ".sh",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", "dist", "build",
    ".venv", "venv", ".claude", ".github",
}


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    query = data.get("query", "")
    if not query:
        return

    # Glob for matching files
    pattern = f"**/{query}*"
    matches = []

    for path in glob.iglob(pattern, recursive=True):
        # Skip unwanted directories
        parts = path.replace("\\", "/").split("/")
        if any(p in SKIP_DIRS for p in parts):
            continue

        # Prioritize known extensions
        _, ext = os.path.splitext(path)
        if ext in PRIORITY_EXTENSIONS:
            matches.insert(0, path)
        else:
            matches.append(path)

        if len(matches) >= 15:
            break

    for match in matches[:15]:
        print(match)


if __name__ == "__main__":
    main()
