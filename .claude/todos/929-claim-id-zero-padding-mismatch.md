<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# claim-todo.ps1 and complete-todo.ps1 disagree on zero-padded ids, so claims are never released

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `complete-todo.ps1` find and delete the claim file that `claim-todo.ps1` actually wrote, so a
completed todo releases its own claim instead of orphaning it.

## Context

Reproduced 2026-09-05 during a `/auto-do-todos` run in
`C:\Users\tecno\Desktop\Projects\sirbepy_blog`, whose backlog uses three-digit zero-padded ids
(`001-`..`007-`).

Observed, in order:

1. `claim-todo.ps1 -Id 002,003,004,005,007 -RepoRoot <repo>` printed
   `Claimed todo 2 (002-dedupe-escapehtml-utility.md) -> .claims\2.claim`. It normalised `002` to
   the integer `2` and named the claim file `2.claim`.
2. `complete-todo.ps1 -Id 002 -RepoRoot <repo>` then printed
   `WARNING: todo 002 is being completed with no claim on record - either it was executed without
   claiming, or the claim was released early`, archived the todo, and left `2.claim` on disk.
3. `ls .claude/todos/.claims/` after completing todo 002 still showed `2.claim`, which had to be
   deleted by hand. Same behaviour for 003, 004 and 005.

So the two halves of the mutex disagree about the claim filename for any zero-padded id:
`claim-todo.ps1` strips the padding when naming the file, `complete-todo.ps1` does not when
looking for it.

Two consequences, and the second is the one that actually bites:

- Every completion emits a false "no claim on record" warning, which trains the reader to ignore a
  warning that is supposed to mean something real.
- The claim file is never released. It ages until it trips the 4-hour + dead-PID staleness rule.
  Until then a second session correctly refuses to touch a todo that is already finished and
  archived - the mutex blocking work on a `done/` item, which is the exact opposite of its purpose.

Backlogs using unpadded ids (`7-`, `12-`, the common case in `~/.claude` itself) are unaffected,
which is why this has not surfaced before.

## Approach

Pick one normalisation and apply it in both scripts - do not fix only the reader.

1. Find where `claim-todo.ps1` builds the claim filename and where `complete-todo.ps1` looks for it
   (both under `~/.claude/skills/close/`, likely sharing `_shared.ps1`).
2. Preferred: put the normalisation in `_shared.ps1` as one function both call, so they cannot drift
   again. Normalising to the UNPADDED form matches what `claim-todo.ps1` already writes, so it
   leaves no existing claim files stranded.
3. Whichever form is chosen, `complete-todo.ps1` must also delete a claim written under the OTHER
   form, so claims already on disk from before the fix still get released.
4. Check the slug-suffixed variant (`<id>-<slug>.claim`) for the same mismatch - the collision path
   builds the name separately.
5. `close/ai-todos-format.md` documents the claim as `.claims/<id>.claim`. If the resolved form is
   "unpadded id", say so there explicitly rather than leaving `<id>` ambiguous.

## Acceptance

- In a scratch backlog containing `001-foo.md`: `claim-todo.ps1 -Id 001` then
  `complete-todo.ps1 -Id 001` leaves `.claims/` empty and prints NO "no claim on record" warning.
- The same sequence with an unpadded id (`7-bar.md`, `-Id 7`) still works - no regression.
- A claim file written in the pre-fix form is still found and deleted by the fixed
  `complete-todo.ps1`.
- The batch form (`-Id 001,002,003`) claims and releases all three cleanly.

## Notes

- Filed from a project session per root `CLAUDE.md` ("a finding about the global `~/.claude` tree
  goes in the `~/.claude` repo's own backlog"). Not fixed there, per the same rule.
- Workaround used on 2026-09-05 in the meantime: delete `.claims/<unpadded-id>.claim` by hand after
  each `complete-todo.ps1` call.
- 2026-09-05, second independent reproduction in `sirbepy_assistant` (TWO-digit padding, `05`/`07`/
  `08`/`10`/`12`), which narrows the root cause to one line. `complete-todo.ps1:217` matches with
  `"^0*$([regex]::Escape($numericId))\.claim$"`. The `0*` tolerates padding on the FILE side but not
  on the ARGUMENT side, and `$numericId` is still the raw padded string, so `-Id 07` compiles to
  `^0*07\.claim$` and cannot match `7.claim`. `-Id 10` and `-Id 12` released correctly in the same
  run: two-digit ids only break when they carry a leading zero, so the trigger is padding present in
  the argument, not id width. Lines 213 and 221 (the `-Slug` and wildcard variants step 4 asks
  about) carry the identical `^0*...` shape, confirming that suspicion.
- That points the fix at step 2's preferred normalisation rather than at the regexes: setting
  `$idBare = [string][int]$numericId` before building all three patterns fixes every variant at once,
  and the existing `0*` then still satisfies acceptance criterion 3 (pre-fix claim files on disk).
  Introduce `$idBare` alongside `$numericId` rather than reassigning it - the archive move and the
  PLAN.md prune both handled padded ids correctly in this run and should not be disturbed.
