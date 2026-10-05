<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=7, reconfirm-count=1, content-hash=8ed3d907 -->
<!-- duplicate-checked: grepped this backlog and done/ for CARGO_TARGET_DIR / "scratch target" / sstest-target, zero hits. done/391-builders-have-no-sanctioned-way-to-get-a-whole-tree-baseline.md is adjacent but a different defect: it was about builders having no sanctioned baseline MECHANISM, and produced the preamble's current "Taking a baseline" clause. This is about that clause's sanctioned escape hatches carrying no cleanup obligation for a scratch target dir specifically. -->
# The builder preamble lets a scratch CARGO_TARGET_DIR leak, and nothing can reclaim it

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `refs/builder-preamble.md` oblige a builder that creates a scratch `CARGO_TARGET_DIR` to remove
it before reporting, the same way it already obliges worktree removal and orphan-process cleanup.

## Context

Found 2026-09-26 during a `/auto-do-todos` run in `server_supervisor`. A builder isolating a linking
bug set `CARGO_TARGET_DIR=C:\tmp\sstest-target`, correctly created and then correctly removed a
scratch git worktree via `safe-remove-worktree.ps1`, and then left the target dir behind at
**7.4 GB**. It flagged it in its own "Out-of-scope findings" as something "the orchestrator may want
to purge later" rather than removing it, and by its own reading of the preamble it was not wrong to.

The preamble's relevant clauses, quoted from `refs/builder-preamble.md`:

- The baseline clause sanctions the escape hatch: "use `git worktree add` to a scratch path instead"
  and names `safe-remove-worktree.ps1` for removing it. It says nothing about a scratch target dir,
  which is the cheaper and more obvious way to get an uncontended Rust build and is what the builder
  actually reached for.
- The cleanup clause is scoped to files, not directories, and is phrased as a RESTRICTION rather than
  an obligation: "Clean up only the exact files you created, by exact name, never by glob or
  wildcard". Its whole purpose is stopping a builder deleting `hooks/.commit-marker-*`. Read
  literally, "only" permits cleaning nothing at all.
- The orphan-check clause is explicitly about PROCESSES ("anything you started that can outlive one
  tool call - Node, `find`, `grep -r`, `adb`, a watcher, a database, any backgrounded process") and
  demands `Get-Process`-style proof. A directory is not a process, so it is out of scope by
  construction.

So a leaked build-artifact directory falls through every clause. It is the disk equivalent of an
orphan process, and the preamble has a hard rule for one and nothing for the other.

**The orchestrator could not remediate it either**, which is what makes this worth fixing rather than
absorbing. `Remove-Item C:\tmp\sstest-target -Recurse -Force` was refused: `Remove-Item on system
path 'C:\tmp' is blocked. This path is protected from removal.` So the guarded path is exactly where
builders naturally put scratch dirs, and neither the builder nor the orchestrator can clean it. It had
to be handed to the dev as a manual `rm`, which is the outcome the preamble's cleanup discipline
exists to avoid.

## Approach

- Add a scratch-build-dir clause to `refs/builder-preamble.md`'s static block, next to the existing
  worktree-removal sentence, since that is where a reader already is when deciding how to get an
  uncontended build. Shape: if you set `CARGO_TARGET_DIR` (or any scratch build/output dir) to a path
  outside the repo, remove it before reporting and paste the command output proving it is gone, the
  same evidence standard the orphan check already demands.
- Prefer directing builders to a path they CAN delete over one they cannot. Check what the removal
  guard actually protects before writing the recommendation: if `C:\tmp` is blocked wholesale, naming
  it in the preamble guarantees the failure above, so name a reclaimable location (a gitignored
  in-repo scratch path, or `$env:TEMP`) and say why.
- Decide, and write down either way, whether the orphan-check paragraph should be widened from
  processes to "processes and scratch directories" rather than adding a separate clause. One clause
  with a broader noun may hold better than a second clause a hurried reader skips, and the preamble
  file's own history is a list of clauses added after each one was skipped.
- Consider whether `/disk-doctor` should know about this class specifically (a large build-artifact
  dir under a temp root, attributable to an agent run). It is advise-only, so it would surface the
  space rather than reclaim it, which is the correct division here.

## Acceptance

- `refs/builder-preamble.md` carries the obligation, and the three markers
  `hooks/dispatch-preamble-guard.py` string-checks still pass unchanged (this adds body text, it must
  not become a fourth marker: that file explicitly argues against raising the rejection surface).
- The recommended scratch location is one that can actually be deleted. Verify by attempting a real
  `Remove-Item` against a throwaway dir at that location, and paste the result.
- The decision on widening the orphan-check noun versus adding a separate clause is recorded in the
  file or this todo, either way.
- `python ci/run_all.py` passes.

## Notes

Filed 2026-09-26 from a `server_supervisor` session, into this repo rather than that project's
backlog, because every file the fix touches lives here (`refs/builder-preamble.md`, possibly
`skills/disk-doctor/`). Per root `CLAUDE.md`'s allocate-by-files rule.

- The leaked directory from the originating incident is `C:\tmp\sstest-target`, 7.4 GB, still on disk
  as of filing. Whoever picks this up can use it as the test case for the reclaimable-location
  acceptance item, but do not assume it is still there.
- The same builder DID handle the worktree correctly via `safe-remove-worktree.ps1`, so this is not a
  builder that ignored the preamble. It followed what was written. That is the argument for treating
  this as a preamble gap rather than a one-off dispatch failure.

- 2026-10-01 recurrence, orchestrator side (claude_usage_in_taskbar /auto-do-todos): the orchestrator itself set CARGO_TARGET_DIR=D:/cargo-target-adt to regenerate ipc.generated.ts past a peer daemon locking D:/cargo-target/debug/claude-conductor.exe, then could NOT purge the 14 GB dir: PowerShell Remove-Item -LiteralPath D:\cargo-target-adt was refused as "system path ... protected from removal" (a harness-level guard, not a hooks/*.py one; it treats any drive-root child as a system path, and the same guard also false-fired on a /auto-do-todos substring inside a -Note string argument). Implication for the fix: whatever rule this todo adds should also name a SANCTIONED scratch location that the removal guard allows (e.g. under C:\tmp or a subdir of the shared target dir), since a drive-root scratch dir is unreclaimable by Claude at all.
