<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Grouping a batch into fan-out dispatches has no completeness check, and silently dropped one item

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a mechanical reconciliation step to the fan-out pattern in `refs/delegation-doctrine.md`, so the
union of what the dispatches cover is checked against the source list before any of them run.

## Context

Surfaced by the `/close` retrospective of the 2026-08-12 `/auto-do-todos` run.

That run had 42 EASY todos and grouped them by target file into 10 builder dispatches, so agents
editing the same file could never collide. The grouping was done by hand, in the orchestrator's head,
by reading down the id list. Todo `75` was never assigned to any group. Nothing detected this: all 10
agents reported success, and the run looked complete.

It was caught only afterward, by accident, while reconciling counts to write the archive notes: the
arithmetic came out at 41 instead of 42, which forced a manual recount of the original list to find
which id was missing. Todo 75 was then done inline and committed separately (`267d5f9`). Nothing was
lost, but only because a bookkeeping step happened to cross-check a number that nothing required it
to cross-check.

The failure mode generalizes to any fan-out where a work list gets partitioned by hand: file-based
grouping, repo-based grouping, dimension-based review. The larger the batch, the more likely it is,
and the harder it is to spot by eye. A 42-item list is already past the point where reading down it
twice is reliable.

## Approach

Add a short "reconcile the partition" step to `refs/delegation-doctrine.md`'s fan-out section, and
reference it from `/auto-do-todos` Step 6 and `/mega-todos` Step A, both of which partition work this
way:

- Before dispatching, write out the union of ids assigned across all groups and diff it against the
  source list. Not "count them", diff them: counts match by coincidence when one item is duplicated
  and another dropped.
- State the expected total in the dispatch plan so the post-run reconciliation has something to check
  against rather than re-deriving it.
- After the fan-out returns, diff the set of ids actually reported on against the same source list.
  An id in neither the completed nor the failed set is a silent drop.

Keep it cheap. This is a set difference the orchestrator can do inline, not a subagent and not a
script, and it should read as three lines in the doctrine rather than a new subsection.

## Acceptance

- `refs/delegation-doctrine.md` states the pre-dispatch and post-dispatch reconciliation, framed as
  a set difference rather than a count comparison.
- `/auto-do-todos` Step 6 and `/mega-todos` Step A both reference it.
- The doctrine says explicitly that an unreported id is a silent drop and must be re-dispatched or
  parked, never assumed done.

## Notes

- Related but distinct from todo 01 (detecting a subagent that died) and todo 50 (session budget on
  fan-outs). Both of those catch an agent that STARTED and then failed. This catches work that was
  never dispatched at all, which no liveness check can see.
- Done 2026-08-13. refs/delegation-doctrine.md gained a Fan-out reconciliation section: enumerate the planned work-item set before dispatch, diff the reported-complete set against it after, as a SET DIFFERENCE and never a count comparison. Cross-referenced from skills/auto-do-todos/SKILL.md Step 6 and skills/mega-todos/SKILL.md Steps C and E. Note the todo's Acceptance named mega-todos 'Step A', but Step A is Preflight and runs before the AUTO queue exists, so the pre-dispatch half went into Step C (Lane assignment), which is the actual partition step.
