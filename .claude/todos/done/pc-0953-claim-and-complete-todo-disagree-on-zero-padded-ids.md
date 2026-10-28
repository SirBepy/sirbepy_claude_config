<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# claim-todo.ps1 and complete-todo.ps1 disagree on zero-padded ids, so a claim leaks

**Type:** skill-improvement
**Origin:** ai

## Goal

A todo whose filename prefix is zero-padded (`08-`, `09-`) should have its claim released when it
completes. Today it does not, and the stale `.claim` file is left behind for the 4-hour staleness
rule to eventually clean up.

## Context

Found 2026-09-05 during a `/mega-todos` run in `C:\Users\tecno\Desktop\Projects\countoff`.

`claim-todo.ps1 -Id 08,09,10,11,27,28` reported:

```
Claimed todo 8 (08-cuts-only-setup-step-with-millisecond-times.md) -> .claims\8.claim
Claimed todo 9 (09-detect-and-adjust-beats-after-all-cuts.md) -> .claims\9.claim
Claimed todo 10 (10-name-the-songs-and-fit-lyrics-as-a-step.md) -> .claims\10.claim
```

It normalised `08` to `8` and wrote `.claims\8.claim`. `complete-todo.ps1 -Id 08` then looked for
`.claims\08.claim`, did not find it, and printed:

> WARNING: todo 08 is being completed with no claim on record - either it was executed without
> claiming, or the claim was released early

Both `8.claim` and `9.claim` were still on disk after all six todos completed, verified by
`ls .claude/todos/.claims/`. Ids `10`, `11`, `27` and `28` are unaffected because they need no
padding, which is exactly why this has gone unnoticed: it only bites single-digit ids, and only in
backlogs old enough to have them.

**The warning is actively misleading.** It names two causes ("executed without claiming", "released
early") and neither is what happened. A run that reads that warning and believes it will conclude
its own claim discipline is broken and go looking in the wrong place.

## Approach

- Normalise the id identically in both scripts. `claim-todo.ps1` already strips the padding, so the
  cheapest fix is for `complete-todo.ps1` to strip it the same way before building the claim path,
  rather than teaching `claim-todo.ps1` to preserve it (which would then break every existing
  unpadded claim file on disk).
- Check `archive-batch.ps1` too, which has the same class of bug one layer up. Passing
  `-Items "08|..."` archived the file correctly but then threw on its own pathspec return:
  `refusing to return pathspec entry '...\done\08-....md' - id prefix '8' was not in the input id
  set`. It compares the resolved file's stripped prefix (`8`) against the caller's raw input (`08`).
  The archival had already happened by then, so the throw only denies the caller its `.Pathspec` -
  in a git-tracked backlog that means the caller cannot commit the archive it just performed.
- Whichever fix lands, cover BOTH directions in whatever check exists: a padded `-Id` against an
  unpadded claim file, and an unpadded `-Id` against a padded one.

## Acceptance

- `claim-todo.ps1 -Id 08` then `complete-todo.ps1 -Id 08` leaves no file in `.claims/` and prints no
  no-claim-on-record warning.
- `archive-batch.ps1 -Items "08|note"` returns a `.Pathspec` naming both halves of the move instead
  of throwing.
- An unpadded id (`-Id 27`) still behaves exactly as it does today. This is the common case and must
  not regress.

## Notes

Not fixed in the session that found it: that was a project session in `countoff`, and global
`~/.claude` rules forbid editing skills or hooks from one. The two leaked claim files were deleted
by hand there so they would not block a later run.
- Archived by /cleanup-todos Pass A on 2026-09-10: premise REFUTED by a live test, not a code read. A triage agent built a scratch backlog at C:\tmp\todo953test and ran the real scripts against it. claim-todo.ps1 -Id 08 printed "Claimed todo 08 (08-test-item.md) -> .claims\08.claim", so the padding is PRESERVED rather than stripped, contradicting the transcript this todo quoted. complete-todo.ps1 -Id 08 then printed "Removed claim 08.claim" and completed cleanly, with no leaked claim file and no misleading warning. Root cause of the original misreading: skills/close/_shared.ps1:16 only normalises padding when the raw id carries a -slug suffix, and complete-todo.ps1:216-217 already matches either padding direction, so the two scripts agree in practice. Falsified theory kept on purpose: a future session that suspects a zero-padding claim leak should re-read this rather than re-derive it.
