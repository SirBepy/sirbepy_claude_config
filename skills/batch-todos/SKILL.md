---
name: batch-todos
description: Triggers on /batch-todos only. Dedupes todos, auto-executes EASY ones after a dry-run confirm, then surfaces the HARD queue.
---

# /batch-todos

> Dedupe AI todos, auto-batch the easy ones, then surface the hard ones for the dev to choose.

Backlog rules (location, format, claims, done/, PLAN.md) live in
`~/.claude/skills/close/ai-todos-format.md` - follow that contract for every file operation here.

## Step 1 - Read todos

Glob `.claude/todos/*.md`. Skip `PLAN.md` and any `done/` subfolder.

If empty: output "No todos found." and stop.

## Step 2 - Dedupe

Read every file's title + Goal section. Flag pairs that describe the same underlying task or the same skill-improvement observation (near-identical titles, overlapping file/target references, same skill pointer for `skill-improvement` type).

For each duplicate pair: keep the one with the more complete Context/Approach (or the lower id if tied), delete the other and prune its PLAN.md line if present. List every deletion: `deleted <id>-<slug>.md - duplicate of <id>-<slug>.md`. If none found, say "No duplicates found."

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

If any listed todo has an active, non-stale claim in `.claims/` (per the contract), mark it `[claimed by another session - will skip]`.

Ask via AskUserQuestion:
- "Looks good, run it" - proceed to step 5
- "Reclassify something" - dev names which todo to move; update and re-present
- "Cancel" - stop, no changes

## Step 5 - Evaluate EASY todos before executing

Dispatch ONE read-only subagent (`model: 'sonnet'`, per the global subagent rule) that reads every EASY todo in full and verifies its premise against the current tree - still valid? actually easy? any downgrade risk (hidden design question, stale assumption, feature that's really HARD)? It returns one verdict per todo with a one-line evidence note:

- **DO** - premise holds, proceed to execution.
- **SKIP** - already done, stale, or superseded. Move to `done/` (create if missing), prune its PLAN.md line, note the evidence; do not execute.
- **FLAG** - real downgrade or open question found. Report it to the dev; re-queue as HARD instead of auto-executing.

Show the DO/SKIP/FLAG breakdown before proceeding to step 6.

## Step 6 - Execute EASY todos

For each **DO**-verdict EASY todo in id order:

1. **Claim it** per the contract's claim protocol. If the claim is lost to a live session, skip with a note and continue.
2. Read the full file. Announce which todo is starting (id + title).
3. Execute the task fully. Touch the claim file's mtime after major steps (heartbeat).
4. Complete per the contract: move the file to `done/` (create if missing), prune its PLAN.md line, release the claim.
5. Run `/commit` after each completed todo.

If a todo hits a blocker: release its claim, surface the blocker, stop that todo, continue with the next EASY.

## Step 7 - Surface HARD todos

Once all EASY todos are done (or if none existed), ask via AskUserQuestion:

Question: "Which todo do you want to tackle next?"
Options: one per HARD todo (id + one-line title). Cap at 4 shown; list extras as plain text below.

If dev picks one: execute inline (same flow as step 6, claim included).
If dev skips: stop. Output remaining HARD todo ids as a reminder.

## Notes

- Source of truth: `.claude/todos/` only.
- This skill executes in id order regardless of PLAN.md ordering - plan-ordered execution is `/pickup`'s job. It still prunes PLAN.md lines of todos it completes.
- Never commit directly. Always use `/commit` after each completed todo.
