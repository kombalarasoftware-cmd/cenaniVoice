# /changelog - Changelog Generation

Generate a user-facing changelog from git history.

## Process
1. Run `git log --oneline -30` (or since last tag/release)
2. Group commits by type (detect conventional commits if used)
3. Transform technical commits into user-friendly descriptions

## Categories
- 🚀 **New Features** — New functionality
- 🐛 **Bug Fixes** — Issues resolved
- ⚡ **Performance** — Speed / efficiency gains
- 🔒 **Security** — Security patches
- 💥 **Breaking Changes** — Requires user action
- 🔧 **Maintenance** — Deps, config, infra

## Output Format
```markdown
## [Version] - YYYY-MM-DD

### 🚀 New Features
- Clear, user-friendly description

### 🐛 Bug Fixes
- What was broken → now fixed
```

## Rules
- Write for **end users**, not developers
- Skip internal refactors, CI changes, typo fixes
- Group related commits into single entries
- Present tense ("Add" not "Added")
