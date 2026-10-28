<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /batch-todos EASY batch (03, 04, 07) never executed - dry-run report was abandoned mid-flow

**Type:** task

## Goal

Execute (or re-derive and then execute) the `/batch-todos` EASY batch that was reported on
2026-07-17/18 but never confirmed, and formally surface the HARD queue to the dev per
`/batch-todos` step 7.

## Context

`/batch-todos` was run on this repo's own `.claude/todos/` backlog. Its dry-run report found: no
duplicates, 3 EASY todos (`03-backfill-skill-9of10-lifts`, `04-reconcile-rate-it-and-commit-below-
threshold`, `07-trim-autopilot-description-budget`), and 5 HARD todos (`06`, `08`, `09`, `11`,
`12`) parked. The report ended with the standard "reply run it / reclassify `<id>` / cancel"
prompt, but the conversation pivoted into designing and building a new `/cleanup-todos` skill
instead (a multi-hour detour: `/brainstorm` -> `/bepy-skill-creator` -> multiple `/rate-it` panels
-> a 7-round `/iterate-it` -> two more rate-fix cycles). No reply to the batch-todos prompt was
ever given. At `/close` time the dev was asked whether to finish this first or close anyway, and
chose to close anyway - hence this todo.

## Approach

Do NOT blindly resume the old report - re-run `/batch-todos` fresh. Time has passed and the
backlog composition changed since that report (todos `11` and `12` didn't exist yet when the
report ran; `13` and `14` were added by a separate concurrent session even more recently). Let
`/batch-todos` step 5's premise-check subagent re-verify `03`/`04`/`07` still hold before executing
anything.

## Acceptance

- The EASY todos from a fresh `/batch-todos` run are either executed and moved to `done/`, or
  explicitly re-classified/skipped with a stated reason.
- The HARD queue is surfaced to the dev per `/batch-todos` step 7 (a table + pick-one-or-done
  prompt), not left implicit.

## Notes

- Dropped via /cleanup-todos 2026-08-11: superseded - references a backlog snapshot that no longer exists. Confirmed by dev 2026-08-11.
