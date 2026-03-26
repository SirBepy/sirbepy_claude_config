---
name: autocommit
description: Enable, disable, or check auto-commit/push mode for the session. Triggers on /autocommit and all its subcommands.
---

# Autocommit Skill

## `/autocommit` - Show State

Print the current autocommit mode. Example output:
```
autocommit: ON (push + version bump)
```
Possible states: `OFF`, `ON (commit only)`, `ON (commit + push)`, `ON (commit + push + version bump)`

---

## `/autocommit on`

Enable autocommit mode. After each logical unit of work is completed, automatically commit using the standard flow (lint, stage by name, prefix). Do NOT push. Stay in this mode until `/autocommit off` is typed.

## `/autocommit off`

Disable all autocommit/autopush modes. Revert to waiting for Joe to ask manually.

## `/autocommit push`

Enable autocommit + push mode. After each logical unit of work, automatically commit and push. No version bump. Stay in this mode until `/autocommit off` is typed.

## `/autocommit pushbump`

Enable autocommit + push + version bump mode. After each logical unit of work:

1. Increment the patch version in `package.json` (e.g. 1.0.0 -> 1.0.1)
2. Stage `package.json` with the other changed files
3. Commit with the version mentioned in the message
4. Push

If no `package.json` exists, skip the version bump and just commit + push. Stay in this mode until `/autocommit off` is typed.

---

## Commit Rules (for all auto modes)

**Prefixes:** FEAT, FIX, REFACTOR, CHORE, DOCS, TEST, STYLE, DATA

**Style:**
- One purpose per commit
- Clear title, no body unless needed
- Never add `Co-authored-by: Claude` or any AI attribution

**Linting:** If a linter exists, run it and fix all issues before committing.

**Shell:** Never chain commands. One command per Bash call. No `&&`, `;`, or `|`.
