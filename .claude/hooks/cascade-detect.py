#!/usr/bin/env python3
"""PostToolUse hook: detect symbols changed in edited files and warn about related locations."""
import json
import os
import re
import subprocess
import sys


def extract_changed_symbols(file_path):
    """Extract function/class/variable names from recent git diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=0", "--", file_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0 or not result.stdout:
            return []

        symbols = set()
        for line in result.stdout.splitlines():
            if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
                continue

            # Python: def func_name, class ClassName
            for match in re.finditer(r"(?:def|class)\s+(\w+)", line):
                symbols.add(match.group(1))

            # TypeScript: function funcName, interface Name, type Name, export
            for match in re.finditer(r"(?:function|interface|type|export\s+(?:const|let|function))\s+(\w+)", line):
                symbols.add(match.group(1))

        # Filter out common/generic names
        generic = {"self", "cls", "args", "kwargs", "None", "True", "False", "return", "import"}
        return [s for s in symbols if s not in generic and len(s) > 2]
    except Exception:
        return []


def find_references(symbol, file_path):
    """Find other files referencing this symbol."""
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.ts", "--include=*.tsx",
             "-l", symbol, "backend/", "frontend/"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return []

        refs = [f for f in result.stdout.strip().splitlines()
                if f and f != file_path and not f.startswith(("node_modules", ".venv", "__pycache__"))]
        return refs[:5]
    except Exception:
        return []


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path.endswith((".py", ".ts", ".tsx")):
        sys.exit(0)

    symbols = extract_changed_symbols(file_path)
    if not symbols:
        sys.exit(0)

    cascades = {}
    for symbol in symbols[:3]:
        refs = find_references(symbol, file_path)
        if refs:
            cascades[symbol] = refs

    if cascades:
        msg = "Cascade alert - related files may need updates:\n"
        for symbol, refs in cascades.items():
            msg += f"  '{symbol}' also used in:\n"
            for ref in refs:
                msg += f"    - {ref}\n"
        print(msg.rstrip())

    sys.exit(0)


if __name__ == "__main__":
    main()
