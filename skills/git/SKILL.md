---
name: git
description: General git operations - staging, branching, reverting, stashing, or anything git-related that isn't a slash command. Triggers when the user says "commit this", "push this", "stage these files", "create a branch", etc. Does NOT handle /commit, /commitpush, or /autocommit - those have their own skills.
---

# Git Skill

Handle ad-hoc git requests from Joe. Use common sense and the context of what he's asking.

## General Rules

- Never chain commands. One command per Bash call. No `&&`, `;`, or `|`.
- Never use `cd` before git commands. Use `git -C /absolute/path <command>` for a specific directory.
- Stage files by name, never `git add -A`.
- Never add `Co-authored-by: Claude` or AI attribution to commits.
- Do not push unless Joe explicitly asks.

## Commit Prefixes (if committing)

- `FEAT:` - new feature
- `FIX:` - bug fix
- `REFACTOR:` - code restructure, no behavior change
- `CHORE:` - maintenance, config, tooling
- `DOCS:` - readme, comments, documentation
- `TEST:` - adding or updating tests
- `STYLE:` - formatting only, no logic change
- `DATA:` - hardcoded data, content, or copy changes
