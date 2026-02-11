#!/bin/bash
# Batch migration script using Claude Code Agent SDK
# Usage: ./batch-migrate.sh <migration-prompt> [file-pattern]
#
# Examples:
#   ./batch-migrate.sh "Convert class components to functional" "src/**/*.tsx"
#   ./batch-migrate.sh "Add type hints to all functions" "backend/**/*.py"
#   ./batch-migrate.sh "Replace axios with fetch API" "frontend/src/**/*.ts"

set -euo pipefail

PROMPT="${1:?Usage: batch-migrate.sh <prompt> [file-pattern]}"
PATTERN="${2:-**/*.py}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"
LOG_DIR=".claude/logs/migrations"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Batch Migration ==="
echo "Prompt: $PROMPT"
echo "Pattern: $PATTERN"
echo "Max parallel: $MAX_PARALLEL"
echo ""

# Find matching files
FILES=$(find . -path "./$PATTERN" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/__pycache__/*" 2>/dev/null || true)
TOTAL=$(echo "$FILES" | wc -l)
echo "Found $TOTAL files to process"
echo ""

# Process files
SUCCESS=0
FAIL=0
RUNNING=0

for file in $FILES; do
    # Wait if at max parallel limit
    while [ "$RUNNING" -ge "$MAX_PARALLEL" ]; do
        wait -n 2>/dev/null || true
        RUNNING=$((RUNNING - 1))
    done

    echo "Processing: $file"
    (
        LOGFILE="$LOG_DIR/${TIMESTAMP}_$(echo "$file" | tr '/' '_').log"
        if claude -p "Apply this change to $file: $PROMPT. Only modify what's necessary. Return OK if successful or FAIL with reason." \
            --allowedTools "Read,Edit" \
            --output-format json > "$LOGFILE" 2>&1; then
            echo "  OK: $file"
        else
            echo "  FAIL: $file (see $LOGFILE)"
        fi
    ) &
    RUNNING=$((RUNNING + 1))
done

wait
echo ""
echo "=== Migration Complete ==="
echo "Logs saved to: $LOG_DIR/"
