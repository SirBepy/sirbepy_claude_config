<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the likely hit, done/914, was closed as a PROSE change to skills/mega-todos/SKILL.md naming /commit step 8. This is 914's Approach item 3, a CODE change to archive-batch.ps1 that 914's own Acceptance did not require. Distinct surface. -->
# archive-batch.ps1 does not refuse a pathspec entry that was not derived from an id

**Type:** task
**Origin:** ai

## Goal

`skills/mega-todos/archive-batch.ps1` can only ever emit paths it derived from a todo id, so a
caller cannot widen the archival pathspec by accident.

## Context

This is todo 914's Approach item 3, deliberately left undone when 914 closed on 2026-09-04 (commit
`ab5f7c1`). 914 was scoped to prose only: it added sentences to `skills/mega-todos/SKILL.md` Step E
and the Barrier COMMIT_MODE section naming `/commit` step 8's working-tree diff check. The builder
correctly reported item 3 as out of scope, since it is a change to a `.ps1` file it did not own and
914's own Acceptance marked it "Consider", not required.

The residual risk it names is real but narrow. `archive-batch.ps1` returns a `.Pathspec` that the
orchestrator passes straight to `git commit -- <paths>`. Today that return value is trusted: nothing
in the script asserts that every emitted path traces back to one of the ids it was actually given.
The danger a directory-wide `git status` pathspec creates (sweeping another session's uncommitted
work into an archival commit) is currently prevented by convention and prose, not by the script.

Worth being honest about the severity: the script already builds its paths from `Resolve-TodoFile`
per id, so there is no known route by which a stray path enters today. This is defence in depth
against a future edit, not a live bug.

## Approach

1. Read `skills/mega-todos/archive-batch.ps1`, specifically how `.Pathspec` is assembled.
2. Add an assertion immediately before the return: every emitted path must either sit under
   `.claude/todos/` with a filename whose id prefix is in the input id set, or be `PLAN.md` (which
   `complete-todo.ps1` prunes on every call and so is always legitimate).
3. On a violation, throw rather than warn, and make the message name the offending path. A silent
   drop would be worse than the status quo, because the caller would commit an incomplete move.

## Acceptance

- A unit-level check proves the assertion fires on a synthetic stray path and stays silent on a
  normal batch.
- An existing multi-id archival still returns both halves of every move plus `PLAN.md`, unchanged.
- `python ci/run_all.py` passes.
