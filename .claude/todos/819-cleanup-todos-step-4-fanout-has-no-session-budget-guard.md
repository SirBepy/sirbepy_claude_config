<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=3, content-hash=04729a6f -->
<!-- duplicate-checked -->
# /cleanup-todos Step 4 dispatches a 6-wide fan-out with no session-budget guard and no interrupted-fan-out recovery

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/cleanup-todos` Step 4 obey the fan-out rules its sibling skills already obey, so a run cannot
lose its entire triage pass to a quota death with nothing recorded.

## Context

2026-08-27. A single `/cleanup-todos` run lost two complete fan-outs. The first (6 agents) died on a
session limit; the retry (4 agents) died ten minutes later on the weekly limit. Both times every
agent returned nothing and the run had no written procedure for it, so the orchestrator improvised.

This is the same defect `done/50-autopilot-guards-context-but-not-session-budget-on-fanouts.md`
fixed, but `/cleanup-todos` was never covered by that fix. Todo 50's own Notes name the skills it
meant to cover: "The same failure would hit `/autopilot` and `/delegate`, since `/auto-do-todos`
adopts `/autopilot`'s behavior contract by reference". `/cleanup-todos` is not in that list and does
not adopt the doctrine, so this is the uncovered sibling rather than a re-file of 50.

Verified against the working tree 2026-08-27:

- `refs/delegation-doctrine.md:180` has a `## Liveness and session budget` section, and `:213` says
  "Context% is not a session-budget signal". The rule exists.
- `grep -n -i 'budget|liveness|dead-dispatch' skills/cleanup-todos/SKILL.md` returns exactly one
  hit, line 174, and it is about claim-file staleness (mtime + PID), not fan-out budget. Step 4
  itself says only to dispatch one subagent per chunk, "all chunks in a single parallel dispatch".

The `DEEP_CHUNK_SIZE = 30` / `DEEP_MAX_CHUNKS = 6` constants make 6-wide the DEFAULT for any backlog
over 150 todos, so this is not an edge case, it is the normal path on a large backlog.

## Approach

Do not restate the doctrine inside this skill. Point at it, the way the other fan-out skills do:

1. In Step 4, before the dispatch, adopt `refs/delegation-doctrine.md`'s "Liveness and session
   budget" section by reference, so width is capped by session budget rather than chunk arithmetic.
2. Add an interrupted-fan-out branch to Step 4: when some chunks return and others die, do NOT
   discard the ones that returned. Write markers for exactly the rows with real verdicts, leave the
   rest unmarked (an unmarked todo already means "not checked"), and have Step 6's report name which
   id ranges were covered. This run did that by improvisation and it was the right call; it should
   be written down rather than re-derived.
3. Consider lowering `DEEP_MAX_CHUNKS` from 6, or having Step 4 issue chunks in two waves instead of
   one parallel dispatch, so a quota death costs half a run rather than all of it. Sequential waves
   also mean the first wave's results are banked before the second can die.

Rejected: a partial-resume mode keyed on which todos already have a fresh marker. Step 5 already
re-scores idempotently and `worth` is explicitly a fresh judgement each run, so resume adds state
for no gain.

## Acceptance

- `skills/cleanup-todos/SKILL.md` Step 4 references the doctrine's liveness/session-budget section
  by name.
- Step 4 has a written branch for "some chunks returned, some died" that banks the partial results.
- A run whose fan-out dies mid-flight still produces a Step 6 report naming which ids were covered
  and which were not.
- Must not regress: the deep/shallow tier split, and Step 5's rule that a shallow row's
  `last-checked` is left unchanged, both stay exactly as they are.

## Notes

- Blocks `[[818-finish-the-cleanup-todos-triage-for-76-unmarked-todos]]`. Running 818 before this is
  fixed will probably reproduce the same death.
