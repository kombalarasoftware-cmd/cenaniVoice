#!/bin/bash
# Extract structured data from codebase using Claude Code Agent SDK
# Usage: ./extract-api.sh [output-file]
#
# Extracts all API endpoints with their methods, paths, auth requirements,
# and descriptions into a structured JSON file.

set -euo pipefail

OUTPUT="${1:-api-endpoints.json}"

echo "=== Extracting API Endpoints ==="

claude -p "Analyze the FastAPI backend in backend/app/api/ and extract ALL API endpoints. For each endpoint include: method (GET/POST/PUT/DELETE), path, auth_required (boolean), description, request_body_schema (if any), response_schema." \
    --output-format json \
    --json-schema '{
        "type": "object",
        "properties": {
            "endpoints": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "path": {"type": "string"},
                        "auth_required": {"type": "boolean"},
                        "description": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["method", "path", "description"]
                }
            }
        },
        "required": ["endpoints"]
    }' \
    --allowedTools "Read,Grep,Glob" | jq '.structured_output' > "$OUTPUT"

echo "Endpoints saved to: $OUTPUT"
echo "Total endpoints: $(jq '.endpoints | length' "$OUTPUT")"
