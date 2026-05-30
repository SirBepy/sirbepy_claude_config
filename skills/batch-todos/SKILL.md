---
name: batch-todos
description: Triggers on /batch-todos only. Classifies ai_todos as EASY (auto-execute) or HARD (dev picks), shows dry-run confirmation, batches all EASY todos, then surfaces the HARD queue.
---

# /batch-todos

> Auto-batch easy AI todos, then surface the hard ones for the dev to choose.

## Step 1 - Read todos

Glob `.for_bepy/ai_todos/*.md`. Skip any `done/` subfolder.

If empty: output "No todos found." and stop.

## Step 2 - Classify

Read each file. Label as EASY or HARD:

| Label | Criteria |
|-------|----------|
| EASY | Self-contained: single file or tightly scoped, no open design questions, no external service calls, no new decisions required, acceptance criteria is clear |
| HARD | Anything else: multi-file, open design question, external service, requires dev input before starting |

When in doubt, label HARD.

## Step 3 - Dry-run confirmation

Show classification before touching anything:

```
EASY (will auto-execute in order):
  01-fix-auth-redirect.md
  04-rename-button-label.md

HARD (queued for you to pick):
  02-redesign-onboarding-flow.md
  05-migrate-database-schema.md
```

Ask via AskUserQuestion:
- "Looks good, run it" - proceed to step 4
- "Reclassify something" - dev names which todo to move; update and re-present
- "Cancel" - stop, no changes

## Step 4 - Execute EASY todos

For each EASY todo in id order:

1. Read the full file.
2. Announce which todo is starting (id + title).
3. Execute the task fully.
4. If `ai_todos/done/` exists: move file there. Otherwise: delete it.
5. Run `/commit` after each completed todo.

If a todo hits a blocker: surface the blocker, stop that todo, continue with the next EASY.

## Step 5 - Surface HARD todos

Once all EASY todos are done (or if none existed), ask via AskUserQuestion:

Question: "Which todo do you want to tackle next?"
Options: one per HARD todo (id + one-line title). Cap at 4 shown; list extras as plain text below.

If dev picks one: execute inline (same flow as step 4).
If dev skips: stop. Output remaining HARD todo ids as a reminder.

## Notes

- Source of truth: `.for_bepy/ai_todos/` only. Never read BEPY_TODOS.md.
- Never commit directly. Always use `/commit` after each completed todo.
