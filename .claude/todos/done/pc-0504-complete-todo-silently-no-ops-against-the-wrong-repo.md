<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=7, reconfirm-count=1, content-hash=2441a387 -->
<!-- duplicate-checked -->
<!-- Read done/98 and done/277 in full: same ROOT CAUSE, different script and a different failure
     mode (silent no-op with exit 0, not a wrong-directory execution). Filed as the third
     recurrence on purpose - see "Why this is not 98 or 277" below. -->
# `complete-todo.ps1` silently no-ops against the wrong repo, and exits 0

**Type:** skill-improvement
**Origin:** ai

## Goal

Make a wrong-`RepoRoot` invocation of `complete-todo.ps1` loud instead of a plausible-looking
success, so a caller cannot believe a todo was archived when it was not.

Secondarily: decide whether the cwd-default-in-a-helper-script pattern deserves one shared fix,
since documenting it twice has not stopped it recurring.

## Context

Hit for real on 2026-08-22, in a `/auto-do-todos` run in
`C:\Users\tecno\Desktop\Projects\hubbub-game-music-guesser` that also had to touch the sibling
platform repo `C:\Users\tecno\Desktop\Projects\hubbub`.

`~/.claude/skills/close/complete-todo.ps1:46` declares:

```powershell
[string]$RepoRoot = (Get-Location).Path,
```

The shell's cwd had drifted to the platform repo (an earlier `cd` inside a compound command; the
harness persists cwd between tool calls). The call was
`complete-todo.ps1 -Id 01 -Note "..."` with no `-RepoRoot`, so it resolved to the platform repo.
It found no live todo `01` there, matched `done\01-implement-claude-design-v3-ui.md` - an
unrelated, long-archived todo that happens to share the numeric id - and printed:

```
Todo 01 already completed (found in done\01-implement-claude-design-v3-ui.md) - skipping move.
Completion bookkeeping done for todo 01.
```

Exit code 0. The real todo was never archived and its Notes line was never written. It was caught
only because the archived filename was obviously unrelated to the work; with a similar slug it
would have passed unnoticed, and the run would have reported a todo as closed that was still open.

Two things combine here, and either alone would be survivable:

1. Numeric ids are per-repo and small, so id collisions across repos are the norm. Every backlog
   has a `01`.
2. Nothing in the output names the repo it acted on, so the message reads as a correct result.

### Why this is not 98 or 277

Both are archived in `done/` and both share the root cause - a repo-scoped command resolving its
target from the shell's cwd in a cross-repo session:

- `done/98-guard-working-directory-for-repo-scoped-commands.md` - `flutter` / `dart run
  build_runner` in the wrong repo. Shipped a real enforcement fix,
  `hooks/flutter-workdir-guard.py` (commit `f9055ac`). Scoped to Flutter/Dart tooling; it cannot
  see a PowerShell helper.
- `done/277-supervised-run-root-default-gotcha.md` - `sv.ps1 ensure`'s `-Root` defaulting to
  `(Get-Location).Path`, launching a second copy of the wrong project. Resolved with
  documentation only (commit `d31c4de`): a callout in `supervised-run/SKILL.md` step 1.

This is a different script and a quieter failure mode - the other two DID something wrong, this
one did nothing while reporting success. Three instances across three scripts is the argument for
step 4 below.

## Approach

Cheapest first; 1 and 2 are worth doing regardless of 3 and 4.

1. **Print the resolved `$RepoRoot` in every message the script emits**, not just failures. A
   one-word change per `Write-Info` turns an invisible wrong-repo run into an obvious one.
2. **Make the "already completed" branch a warning, not a silent success** (`complete-todo.ps1`,
   the `$doneMatches.Count -eq 1` branch around line 174). It is currently indistinguishable from
   a real archive in both exit code and tone. It should say plainly that NOTHING was moved and NO
   note was appended.
3. Consider defaulting `$RepoRoot` from `git rev-parse --show-toplevel` rather than
   `(Get-Location).Path` - cwd is not the repo, and a call from a subdirectory has the same bug.
   Check the sibling helpers before changing only this one: `claim-todo.ps1` and
   `reserve-todo-id.ps1` take `-RepoRoot` too, and `sv.ps1` takes `-Root`.
4. **Decide the pattern-level question.** Either (a) accept per-script hardening and do 3
   everywhere, or (b) add one line to `close/ai-todos-format.md` making `-RepoRoot` mandatory in
   any session touching more than one repo, or (c) a `PreToolUse` hook shaped like
   `flutter-workdir-guard.py` that flags any `close/*.ps1` call with no explicit `-RepoRoot`.
   Note 277 already tried (b)'s equivalent for `sv.ps1` and this incident happened anyway - weigh
   that before picking documentation a third time.

## Acceptance

- Running `complete-todo.ps1 -Id <n>` from a cwd outside the intended repo either fails loudly, or
  prints the resolved repo root prominently enough that a reader catches it.
- The "already completed" path no longer reads as a successful archive.
- The happy path is unchanged: a correct call still appends the note, moves the file to `done/`,
  prunes PLAN.md, and releases the claim. Verify against a scratch copy of a real backlog.
- A written answer to step 4 exists, even if the answer is "per-script, no shared guard".

## Notes

Surfaced by `/close` Phase 1 (skill rule violations) during a `/respawn` out of the music-guesser
session. Filed here rather than in the project backlog per root `CLAUDE.md`: a finding about the
global `~/.claude` tree belongs to `~/.claude`'s own backlog.

The immediate instance was recovered by re-running with an explicit
`-RepoRoot "C:\Users\tecno\Desktop\Projects\hubbub-game-music-guesser"`, which archived the todo
correctly. No data was lost.
- Done via /mega-todos batch 3, commit 0f8a590: complete-todo.ps1 prints its resolved repo root in every message, and the already-completed branch is now a warning stating nothing was moved instead of an info line that read as success. Pattern-level decision recorded in the builder report.
