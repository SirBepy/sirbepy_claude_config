---
name: batch-todos
description: Triggers on /batch-todos only. Dedupes ai_todos, classifies survivors as EASY (auto-execute) or HARD (dev picks), shows dry-run confirmation, batches all EASY todos, then surfaces the HARD queue.
---

# /batch-todos

> Dedupe AI todos, auto-batch the easy ones, then surface the hard ones for the dev to choose.

## Step 1 - Read todos

Glob `.for_bepy/ai_todos/*.md`. Skip any `done/` subfolder.

If empty: output "No todos found." and stop.

## Step 2 - Dedupe

Read every file's title + Goal section. Flag pairs that describe the same underlying task or the same skill-improvement observation (near-identical titles, overlapping file/target references, same skill pointer for `skill-improvement` type).

For each duplicate pair: keep the one with the more complete Context/Approach (or the lower id if tied), delete the other. List every deletion: `deleted <id>-<slug>.md - duplicate of <id>-<slug>.md`. If none found, say "No duplicates found."

## Step 3 - Classify

Read each file. Label as EASY or HARD:

| Label | Criteria |
|-------|----------|
| EASY | Self-contained: single file or tightly scoped, no open design questions, no external service calls, no new decisions required, acceptance criteria is clear |
| HARD | Anything else: multi-file, open design question, external service, requires dev input before starting |

When in doubt, label HARD.

## Step 4 - Dry-run confirmation

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
- "Looks good, run it" - proceed to step 5
- "Reclassify something" - dev names which todo to move; update and re-present
- "Cancel" - stop, no changes

## Step 5 - Execute EASY todos

For each EASY todo in id order:

1. Read the full file.
2. Announce which todo is starting (id + title).
3. Execute the task fully.
4. If `ai_todos/done/` exists: move file there. Otherwise: delete it.
5. Run `/commit` after each completed todo.

If a todo hits a blocker: surface the blocker, stop that todo, continue with the next EASY.

## Step 6 - Surface HARD todos

Once all EASY todos are done (or if none existed), ask via AskUserQuestion:

Question: "Which todo do you want to tackle next?"
Options: one per HARD todo (id + one-line title). Cap at 4 shown; list extras as plain text below.

If dev picks one: execute inline (same flow as step 5).
If dev skips: stop. Output remaining HARD todo ids as a reminder.

## Notes

- Source of truth: `.for_bepy/ai_todos/` only.
- Never commit directly. Always use `/commit` after each completed todo.
