---
description: Create a PR with auto-generated summary from git diff analysis (like Copilot PR Summary)
---

# /create-pr - Auto-Generate PR with Summary

Create a pull request with AI-generated description from commit analysis.

## Process
1. Get current branch: `!git branch --show-current`
2. Verify not on main: abort if on main branch
3. Get full diff against main: `!git diff main...HEAD --stat`
4. Get detailed diff: `!git diff main...HEAD`
5. Get commit history: `!git log main..HEAD --oneline`
6. Read the most important changed files to understand changes deeply
7. Categorize changes: feature, bugfix, refactor, docs, infra, test
8. Detect breaking changes, migration needs, deployment notes
9. Generate PR via `gh pr create` with the template below

## PR Body Template
```
## Summary
<1-3 sentence overview focusing on WHY, not just WHAT>

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Refactoring
- [ ] Documentation
- [ ] Infrastructure/CI

## Changes
<Bulleted list grouped by area: Backend, Frontend, Infrastructure>

## Files Changed
<Each file with 1-line description>

## Testing
<What was tested and how to verify>

## Deployment Notes
<Breaking changes, migration steps, env var changes, or "None">
```

## Rules
- Title: under 70 chars, imperative mood (e.g., "Add campaign batch processing")
- Summary: focus on WHY and impact, not just listing files
- Always flag breaking changes prominently
- Include migration steps if DB schema changed
- Include new env vars if added
- Push branch with -u flag before creating PR
