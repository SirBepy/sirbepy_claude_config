<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=9f429e89 -->
<!-- duplicate-checked: searched this backlog for complete-todo, batch and reserve-todo-id. Nothing covers the error message on a rejected multi-id call. -->
# 1015 - complete-todo.ps1 rejects a batch -Id with a misleading error

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-25

## Goal

A caller who passes a comma-separated `-Id` to `complete-todo.ps1` is told the batch form is not
supported, instead of being told the todo does not exist.

## Context

Hit on 2026-09-25 in a zng-app session that had just finished six todos in one commit. The session
had claimed all six in ONE call, because `claim-todo.ps1` supports that:

```
claim-todo.ps1 -Id 184,163,83,76,185,75    # works, claims all six
```

The symmetrical completion call failed:

```
complete-todo.ps1 -Id 184,163,83,76,185,75
Write-Fail : No todo file matching id '184,163,83,76,185,75' found in ...\.claude\todos or ...\done.
```

**The refusal itself is correct and deliberate**, not a bug. `complete-todo.ps1:20-21` says the
`[string[]]` type exists only to "match claim-todo.ps1's -Id" and that "an array is joined back
into a single id and is not a batch-complete form", and `:57-58` repeats it at the join. The
script is doing exactly what it documents.

The DEFECT is the error message. `$Id` has already been collapsed to `184,163,83,76,185,75` by
the time the lookup fails, so the script reports a missing todo, which sends the caller looking
for a filesystem or id problem that does not exist. The real cause, "you passed a batch to a
script that only completes one", is stated only in a comment inside the source.

`close/ai-todos-format.md` documents the batch form under Claims and nowhere else, so the doc is
already consistent. The asymmetry is a reasonable thing for a caller to assume, and it will keep
being assumed - the fix is to make the failure say so in one line, not to add batch completion.

## Approach

In `complete-todo.ps1`, before the join at line ~57: if the raw `-Id` contains a comma (either as
a multi-element array or as one comma-bearing string), fail immediately with a message naming the
real cause and the right call shape, e.g.

```
ERROR: -Id takes one todo per call; complete-todo.ps1 has no batch form (see the note at the top
of this script). Call it once per id: foreach ($id in 184,163) { complete-todo.ps1 -Id $id }
```

Keep the existing `[string[]]` binding and the join for the single-id-as-array case, so a caller
passing `-Id 184` as a one-element array still works. Do not add batch completion: the per-id
PLAN.md pruning and claim release are written as a single-id sequence, and widening that is a
much larger change than this todo's finding justifies.

Consider whether `reserve-todo-id.ps1` has the same asymmetry while in there.

## Acceptance

- `complete-todo.ps1 -Id 07,08` prints the batch-not-supported message and exits non-zero, without
  the misleading "no todo file matching" line.
- `complete-todo.ps1 -Id 07` still archives todo 07 exactly as today.
- `python ci/run_all.py` passes.
