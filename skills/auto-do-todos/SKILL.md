---
name: auto-do-todos
description: Grinds through question-free todos autonomously until ~40% ctx, then tops up by asking, then runs code-check and tests to verify.
disable-model-invocation: true
---

# /auto-do-todos

> Only touch todos that need no dev decision; batch every question that remains into one ask.

**Trigger:** `/auto-do-todos` only. Never auto-invoke.

## Order of operations

1. Record `START_SHA` (`git rev-parse HEAD`) - the wrap-up phase diffs against it.
2. Run `/cleanup-todos` in full, including its own confirm gate.
3. Run `/batch-todos` in full, including its own dry-run confirm and EASY execution. Its HARD queue (step 7 output) is the candidate pool below.
4. Triage the HARD queue (Step 4).
5. Branch on the question-free count: execute now, or ask-first (Step 5).
6. Top-up loop once the question-free queue is exhausted (Step 6).
7. Wrap-up verification (Step 7).
8. Written summary (Step 8).

## Step 4 - Triage the HARD queue

Dispatch ONE subagent (`model: 'sonnet'`) with the full text of every HARD todo `/batch-todos` surfaced. For each, it returns:

- `question_free`: true/false - would executing this actually require a UX/ARCH/SEC/DATA/TOOLING decision from the dev? Internal implementation judgment that a bounded `/iterate-it` can resolve on its own still counts as question-free, same tiering `/autopilot` uses - only a genuine fork the dev must pick counts as `false`.
- If `false`: the actual question(s) it would need, each tagged with a domain per the global `[UX]/[ARCH]/[SEC]/[DATA]/[TOOLING]` convention, plus a recommended option where there is one.
- `priority`: High/Med/Low, same urgency read as `/batch-todos` step 7.

When in doubt, mark `question_free: false` - a false positive here means silently guessing on something the dev should have decided.

## Step 5 - Execute or ask-first

Count the `question_free: true` todos.

**Fewer than 5:** don't execute anything yet. Batch every needs-question todo's question(s) via `AskUserQuestion` (4 per call, High priority first, chain calls past 4). Once the dev answers, fold the now-unblocked todos into the queue below and continue.

**5 or more:** execute the question-free queue now, High to Low priority. Per todo:

1. Claim it per `close/ai-todos-format.md`.
2. Execute via a subagent, following `/autopilot`'s behavior contract in full by reference (delegation doctrine, tiered uncertainty resolution via bounded `/iterate-it`, nested-question suppression as a safety net if a todo was mis-triaged, verify-before-done) - except its context thresholds, which this skill overrides (below).
3. `/commit` after each completed todo.
4. Run `node ~/.claude/skills/context-left/context-left.mjs` and read pct used.
   - **>= 40% used:** stop the queue immediately, even with todos left, and go to Step 7.
   - Otherwise: next todo.

Queue empties before 40%? Go to Step 6.

## Step 6 - Top up to 30%

Read ctx used (same script).

- **>= 30% used:** go to Step 7.
- **< 30% used:** cheap headroom remains. Pick the highest-priority remaining needs-question todo(s), batch their question(s) via `AskUserQuestion` (domain-tagged, 4 per call), and add a "stop here" option to every batch so the dev can halt without answering the rest. On answers, execute those todos (same subagent + commit + context-check loop as Step 5). Recheck ctx used after each. Repeat - next priority tier, ask, execute - until ctx used reaches 30%, the needs-question queue is exhausted, or the dev picks "stop here" (or otherwise signals stop).

## Step 7 - Wrap-up verification

Once execution stops (ceiling hit, queue exhausted, or dev-interrupted), dispatch subagents to verify the run's whole diff (`git diff START_SHA..HEAD`):

1. `/code-check START_SHA..HEAD` - structural + convention review, writes findings straight to the todos backlog.
2. The project's fast-check floor (typecheck, unit tests, lint, build) - whichever the project actually has.
3. E2E tests if the project has a runnable suite (`test-flow`, `flutter-e2e`, or an existing Playwright/Cypress config) - best effort, skip with a one-line note if there's no headless way to run them.

Fix anything trivial and re-verify inline. Anything needing a dev decision goes through the same triage-and-batch pattern as Step 6, never a guess.

## Step 8 - Summary

End with one written summary: todos completed (with commit shas), todos skipped/parked and why, questions asked and the answers applied, final ctx% used, and the wrap-up verification result (code-check finding count, test/e2e pass-fail).

## Notes

- Never invoke `/autopilot` as a literal slash command here - its "auto-answer everything, never ask" contract is the opposite of this skill's "skip anything that needs asking" rule. Steps 5/6 reuse its documented CONTRACT by reference, with this skill's own 30%/40% thresholds instead of autopilot's 50%/60%.
- Never commit directly. `/commit` after each completed todo, same cadence as `/batch-todos`.
- Source of truth for the backlog: `.claude/todos/` per `close/ai-todos-format.md`.
