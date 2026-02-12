---
description: Load a task-specific context space for focused work (like Copilot Spaces)
---

# /space - Load Context Space

Load a context space for focused, task-specific work: $ARGUMENTS

## Process
1. If no argument given, list available spaces: `ls .claude/spaces/`
2. If argument given, load the space:
   a. Read `.claude/spaces/$ARGUMENTS/CONTEXT.md` for task instructions and key files
   b. Read `.claude/spaces/$ARGUMENTS/notes.md` if it exists for additional context
   c. Read all files listed in the "Key Files" section of CONTEXT.md
   d. Apply the instructions from the space for this session
3. If space does not exist, offer to create it:
   a. Ask what the task/focus area is
   b. Ask which files are most relevant
   c. Create CONTEXT.md and notes.md with the provided information

## Creating a New Space
When creating `.claude/spaces/<name>/CONTEXT.md`:

```markdown
---
description: Brief description of the task
---

# Space Name

## Focus Area
What this space is about and the goal.

## Key Files (always read these first)
- path/to/important/file1.py
- path/to/important/file2.ts

## Related Issues
- Issue descriptions or GitHub issue numbers

## Instructions
- Task-specific rules and guidelines
- Things to watch out for
- Patterns to follow
```

## Rules
- Each space is a self-contained context for a specific task
- Spaces persist across sessions via the file system
- Read ALL key files listed in CONTEXT.md when loading a space
- Apply space-specific instructions for the duration of the session
