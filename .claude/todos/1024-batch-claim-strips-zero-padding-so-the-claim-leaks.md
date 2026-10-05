<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=8, reconfirm-count=1, content-hash=f862bbaf -->
<!-- duplicate-checked: 929 and 953 in done/ were both archived as REFUTED on 2026-09-10 on the strength of live scratch-backlog tests. Those tests were correct AND their conclusion was wrong to generalise: both ran claim-todo.ps1 with a SINGLE padded id, which genuinely works. This todo reproduces the defect in the BATCH form, which neither of them tested, side by side against the single form in the same session. It is not a re-file of a refuted premise; it is the case the refutations missed, and it names why they missed it. -->
# Batch claim-todo.ps1 strips zero padding, so a padded id's claim leaks and complete-todo warns falsely

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `claim-todo.ps1`'s BATCH form name a padded id's claim file the same way its single-id form
already does, so `complete-todo.ps1` finds and releases it instead of leaking the file and printing a
warning that names two causes, neither of which happened.

## Context

Hit 2026-09-26 during an `/auto-do-todos` run in
`C:\Users\tecno\Desktop\Projects\roblox-trend-pipeline`, then isolated in scratch repos the same
session. This supersedes the refutations in `done/929-claim-id-zero-padding-mismatch.md` and
`done/953-claim-and-complete-todo-disagree-on-zero-padded-ids.md`.

**The distinguishing variable is the batch form, not the padding width.** Both halves below were run
minutes apart, same session, same scripts, fresh `git init` scratch backlogs:

```
=== ct1: SINGLE padded id (the form both 2026-09-10 refutations tested) ===
> claim-todo.ps1 -Id 07 -RepoRoot C:\tmp\ct1
Claimed todo 07 (07-alpha.md) -> .claims\07.claim          <-- padding PRESERVED
> complete-todo.ps1 -Id 07 -RepoRoot C:\tmp\ct1 -Note "t"
[C:\tmp\ct1] Removed claim 07.claim
  claims left: ''                                          <-- clean

=== ct2: BATCH containing a padded id (the form /auto-do-todos actually uses) ===
> claim-todo.ps1 -Id 08,20 -RepoRoot C:\tmp\ct2
Claimed todo 8 (08-beta.md) -> .claims\8.claim             <-- padding STRIPPED
Claimed todo 20 (20-gamma.md) -> .claims\20.claim
> complete-todo.ps1 -Id 08 -RepoRoot C:\tmp\ct2 -Note "t"
[C:\tmp\ct2] WARNING: todo 08 is being completed with no claim on record - either it was
             executed without claiming, or the claim was released early
  claims left: '20.claim, 8.claim'                         <-- 8.claim leaked
```

Note the single-id line prints `Claimed todo 07` and the batch line prints `Claimed todo 8`. The
normalisation is visible in the log message itself, which is why this is cheap to spot once the
batch form is the thing under test.

The original production occurrence, same shape: `claim-todo.ps1 -Id 07,20,33,36` printed
`Claimed todo 7 (07-plan-e-scope-grant-automation.md) -> .claims\7.claim` alongside
`Claimed todo 20 ... -> .claims\20.claim`. Later, `complete-todo.ps1 -Id 07` warned and left
`7.claim` behind, which had to be deleted by hand, while `-Id 20`, `-Id 33`, `-Id 36` and `-Id 29`
all printed `Removed claim <id>.claim` and released cleanly.

**Why this matters more than a leaked file.** The batch form is not an exotic path, it is the one the
contract mandates. `close/ai-todos-format.md`'s Claims section requires it ("Handling N todos in one
pass costs one remembered claim call... claim every id in the batch up front, in a single
`claim-todo.ps1` invocation"), and `/auto-do-todos` Step 6 and `/batch-todos` Step 6 both instruct it
verbatim. So the broken path is the prescribed one and the working path is the one a caller is told
not to use.

Two harms, second worse:

1. A false warning, on correct usage, that trains readers to ignore it.
2. A leaked lock. Per the staleness rule a claim is only reclaimable once mtime exceeds 4 hours AND
   the PID is dead. More importantly `/cleanup-todos` Step 5 skips a marker write when it sees a live
   claim, and its Step 7 claims-checks immediately before archiving, both keyed on the id it was
   given. Asked about `07` it will not see `7.claim`, so it can archive a todo a live session is
   working from. That is the same bug in a more dangerous position and is the real reason to fix it.

**Root cause, not yet read and therefore UNVERIFIED:** `done/953`'s note records that
`skills/close/_shared.ps1:16` normalises padding only when the raw id carries a `-slug` suffix, and
that `complete-todo.ps1:216-217` matches `"^0*$([regex]::Escape($numericId))\.claim$"`, whose `0*`
tolerates padding on the FILE side but not the ARGUMENT side. That reading was made against the
single-id path. Whether the batch loop takes a different branch, or casts each element to `[int]`
while splitting the comma list, has NOT been read this session. Read it before fixing.

## Approach

1. Read `claim-todo.ps1`'s comma-split/batch branch and find where an element loses its padding that
   the single-id branch does not. Do not fix from `done/953`'s root-cause note; it describes the path
   that works.
2. Fix it at the split, so every element goes through the identical normalisation the single-id path
   uses. One shared helper in `_shared.ps1` that both branches call is the version that cannot drift
   again; two parallel implementations is how this arrived.
3. Keep `complete-todo.ps1`'s existing `^0*...` tolerance on READ, so `8.claim` files already on disk
   in any repo are still found and released rather than stranded by the fix.
4. Apply the same check to the slug-suffixed variant (`<id>-<slug>.claim`), which the batch form
   documents as its collision escape hatch (`-Id 03,434-real-slug,05`), so a batch mixing both id
   shapes is covered.
5. Check `archive-batch.ps1` for the same class of defect: `done/953` recorded it throwing
   `id prefix '8' was not in the input id set` for `-Items "08|..."`, comparing a stripped prefix
   against a raw input. Unverified this session, same family, worth one test.

## Acceptance

- In a scratch backlog holding `08-beta.md` and `20-gamma.md`: `claim-todo.ps1 -Id 08,20` writes
  `08.claim` and `20.claim`, and `complete-todo.ps1 -Id 08` prints `Removed claim 08.claim`, leaves
  `.claims/` holding only `20.claim`, and prints NO no-claim-on-record warning.
- The single-id form still behaves exactly as it does today (`-Id 07` to `07.claim` to released), and
  an unpadded batch (`-Id 10,20,30`) still does too. Both are the no-regression cases.
- A pre-fix `8.claim` sitting on disk is still found and released by `complete-todo.ps1 -Id 08`.
- A batch mixing a padded id and a full slug stem claims and releases both.
- `python ci/run_all.py` stays green.
- Add the batch case to whatever test covers this, not just the single-id case. The absence of a
  batch test is the actual defect here; the padding is a symptom.

## Notes

Filed from a project session per root `CLAUDE.md`: a finding about the global `~/.claude` tree goes in
this repo's own backlog, and a project session does not edit the scripts itself. The leaked
`7.claim` in `roblox-trend-pipeline` was deleted by hand on 2026-09-26.

**Process lesson, worth more than the fix.** `done/929`'s own closing note already warns
"re-verify a reproduction before scoring it" after a triage pass scored it 9/10 off a stale
transcript. Both todos were then archived by tests that re-verified the wrong invocation: they proved
the single-id path clean and concluded the defect did not exist, rather than concluding the defect did
not exist *on that path*. A refutation is only as broad as the call it actually made, and the call it
should have made was the one the contract mandates. When archiving a todo as refuted, check that the
reproduction attempted matches the invocation the original report quoted; here the quoted transcripts
in both 929 and 953 plainly showed a comma-separated `-Id`, and both tests used a single id.

- Root cause confirmed live (/cleanup-todos 2026-10-05, folded from archived duplicate 1072): an unquoted `-Id 16,13,15,01` is parsed by PowerShell as an integer array before the script runs, so `01` arrives as `1`; quoting the list (`-Id "16,13,15,01"`) preserves the padding. The regex in `_shared.ps1` is not the cause.
