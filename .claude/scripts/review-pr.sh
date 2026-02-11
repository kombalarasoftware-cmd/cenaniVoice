#!/bin/bash
# Automated PR review using Claude Code Agent SDK
# Usage: ./review-pr.sh <pr-number>
#
# Features:
#   - Security review (OWASP Top 10)
#   - Code quality check
#   - Performance analysis
#   - Architecture consistency
#
# Example: ./review-pr.sh 42

set -euo pipefail

PR_NUMBER="${1:?Usage: review-pr.sh <pr-number>}"

echo "=== Reviewing PR #$PR_NUMBER ==="

# Get PR diff
DIFF=$(gh pr diff "$PR_NUMBER")

if [ -z "$DIFF" ]; then
    echo "Error: Could not fetch PR diff"
    exit 1
fi

# Run security review
echo ""
echo "--- Security Review ---"
echo "$DIFF" | claude -p \
    --append-system-prompt "You are a security engineer. Review this PR diff for: SQL injection, XSS, command injection, auth bypass, secrets exposure, CORS issues. Output findings as markdown with severity levels." \
    --output-format json | jq -r '.result'

# Run quality review
echo ""
echo "--- Code Quality Review ---"
echo "$DIFF" | claude -p \
    --append-system-prompt "You are a senior engineer. Review this PR diff for: error handling, type safety, naming, DRY violations, N+1 queries, missing tests. Output findings as markdown." \
    --output-format json | jq -r '.result'

echo ""
echo "=== Review Complete ==="
