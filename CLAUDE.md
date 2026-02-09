# VoiceAI Platform - Project Rules

## Claude CLI Features Integration
> Generic system — works with any project, any language. Portable across workspaces.

### Memory System
- **On conversation start**: Read `.claude/memory.md` for persistent context
- **During work**: Update `memory.md` when you discover important decisions, gotchas, or architecture patterns
- Format entries as `[YYYY-MM-DD] Description`
- Keep it concise — archive entries older than 30 days

### Hooks System
- **Before editing**: Check `.claude/hooks.json` → `pre_edit` hooks matching the file pattern
- **After editing**: Check `post_edit` hooks
- **Before commit**: Check `pre_commit` hooks
- **After file create**: Check `post_create` hooks
- Only run hooks where `"enabled": true`
- Replace `{file}` with actual file path, `{dir}` with file's directory
- If hook fails and `stop_on_failure` is true, report error before continuing

### Custom Commands
When user types `/commandname`, read `.claude/commands/commandname.md` and execute:
- `/review` — Code review (file or git diff)
- `/deploy` — Pre-deployment checklist
- `/refactor` — Analyze & restructure code
- `/test` — Generate tests
- `/changelog` — Generate changelog from git
- `/security` — Security audit

If the command file doesn't exist, inform the user.

---

## Language Policy
- **No Turkish anywhere** - all UI text, code comments, API descriptions, docstrings, log messages, and prompt instructions must be in English
- **No exceptions** - even domain-specific terms must use English equivalents (Mr/Mrs, not Bey/Hanim)
- The AI agent's spoken language is controlled by the `language` setting, not by the instruction language
