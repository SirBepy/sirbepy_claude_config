<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# claim-todo.ps1 and complete-todo.ps1 duplicate the prefix-less-stem fallback

**Type:** task
**Origin:** ai

## Goal

Collapse the duplicated prefix-less-filename fallback in the two `skills/close/` PowerShell scripts
onto one shared helper, so a change to the rule cannot land in one script and miss the other.

## Context

Found by `/code-check` on 2026-08-25, reviewing commit `c1cf830` (todo 393).

Both scripts gained a near-identical ~14-line block:

- `skills/close/claim-todo.ps1:63-78`
- `skills/close/complete-todo.ps1:123-137`

Same shape in both: build a `^<regex-escaped stem>\.md$` pattern, re-scan the backlog when the
numeric-id pattern found nothing, emit a `Write-Warning` naming `reserve-todo-id.ps1` as the fix,
and null out `$Slug`. The reviewer checked `skills/close/` for an existing shared PowerShell module
to extract into and found none (`reserve-todo-id.ps1` is unrelated - it allocates ids, it does not
resolve them).

**This is not urgent, and the todo says so deliberately.** Two copies of fourteen lines is cheap;
the cost is drift, and drift only bites when someone edits the rule. The specific hazard worth
naming: the two copies are NOT symmetrical. `complete-todo.ps1` must also reassign `$idPattern`
(because its `done/` fallback branch reuses that variable further down) while `claim-todo.ps1` does
not. Anyone "deduplicating" these by eye without noticing that asymmetry will break the
already-completed detection path.

## Approach

1. **Trigger, not now:** do this when a third caller appears, or when either copy needs editing
   anyway. Extracting for its own sake spends risk on a load-bearing script pair with no test suite,
   for no behaviour gain.
2. When it happens: create `skills/close/_shared.ps1` (dot-sourced, not a module - these are scripts
   invoked directly, not imported) holding a `Resolve-TodoFile` that takes the backlog dir, the id
   and an optional slug, and returns the matched file plus a flag for whether the prefix-less
   fallback fired.
3. Preserve the asymmetry above explicitly: the helper returns the pattern it matched on so
   `complete-todo.ps1` can keep using it for its `done/` branch. Do not assume the two callers want
   identical post-match state.
4. Verify in a scratch repo, the way `393` was: a prefix-less file and a normal numeric id, through
   BOTH claim and complete, checking the warning fires and normal ids are untouched.

## Acceptance

- One definition of the fallback, dot-sourced by both scripts.
- A prefix-less todo can still be claimed and archived, with the warning.
- A numeric id, a `<id>-<slug>` stem, and an ambiguous colliding id all behave exactly as before.
- `python ci/run_all.py` passes (it does not cover these scripts, so state that too rather than
  treating a green run as evidence).

## Notes

`/code-check` classed this structural (class 2) and filed rather than applied it, because the route
for class 2 requires naming a test that would fail if the change were wrong - and there is no
`test_*.ps1` anywhere for `skills/close/`. That absence is the real risk here and is itself close to
todo `501`'s territory (live guards with no test file).
