<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=7, reconfirm-count=1, content-hash=0b5b212c -->
<!-- duplicate-checked: done/855 built archive-batch.ps1 and done/919 added its id-derivation assertion. Neither touches what .Pathspec omits. This is the caller-side gap both left. -->
# archive-batch.ps1's .Pathspec omits the deletion half, so every caller hand-builds it

**Type:** skill-improvement
**Origin:** ai

## Goal

`archive-batch.ps1` returns a pathspec a caller can pass straight to `git commit` with no further
assembly, so archiving a batch is one call plus one commit.

## Context

Observed 2026-09-04 across six archival barriers in a single `/mega-todos` run.

`archive-batch.ps1`'s docstring says it "names both halves of the move for the commit pathspec - the
source under `.claude/todos/` and the destination under `done/`". In practice `.Pathspec` contains
only paths that **still exist on disk**, which after the move means the `done/` destinations plus
`PLAN.md`. The source paths are gone, so they are correctly excluded by that rule and incorrectly
absent from the pathspec, because git still needs them named to record the deletion.

That omission is deliberate and documented (an untracked source has no delete to stage, which
aborted a caller's `git add` on todo 848). The problem is that it leaves every caller to
reconstruct the missing half. In this run that meant the same shell loop six times:

    for i in $IDS; do ls .claude/todos/done/$i-*.md; git diff --name-only --diff-filter=D -- ".claude/todos/$i-*.md"; done

A step repeated six times by hand, in a skill whose whole point is that the helper owns this, is the
signal this todo exists for. It is also error-prone in the direction that fails silently: forget the
deletion half and you get a half-committed move, exactly the shape `/commit` step 8's staged-pathspec
coverage check exists to catch.

## Approach

1. Read `skills/mega-todos/archive-batch.ps1`, specifically how `.Pathspec` is assembled and the
   todo-848 guard that filters to existing paths.
2. Emit the source path too, but only when git will actually accept it: the file was TRACKED before
   the move. `git ls-files --error-unmatch <source>` answers that, and an untracked source stays
   excluded exactly as today, so todo 848's fix is preserved rather than reverted.
3. Update `/mega-todos` Step E to pass `.Pathspec` directly, deleting the reconstruction loop from
   the documented procedure.

## Acceptance

- `.Pathspec` for a batch of tracked todos names both halves of every move plus `PLAN.md`, and a
  `git commit -- $result.Pathspec` records the renames with nothing left staged afterwards.
- An untracked source still does not appear, and the todo-848 case (helper does not abort) still
  holds. Cover both in the verification, not just the happy path.
- `/mega-todos` Step E no longer instructs the caller to rebuild the deletion half.

## Notes

Verify against a scratch fixture, never by archiving a real todo. A live `/mega-todos` run uses this
script at every barrier, and a regression here corrupts that run's own bookkeeping (todo 919's
dispatch hit the same constraint).
- DONE 2026-09-10 via /loop-todos cycle 1. skills/mega-todos/archive-batch.ps1:132-142 no longer asks whether the source file EXISTS, which could never be true: complete-todo.ps1 has already moved it by the time that line runs, so Test-Path was structurally guaranteed false and a tracked source deletion never entered the pathspec. It now asks whether the source was TRACKED, via git ls-files --error-unmatch, which reads the index rather than the working tree and therefore still answers correctly after the move. An untracked source still exits non-zero and stays excluded, preserving todo 848 fix exactly. The try/catch around it is not decoration: under ErrorActionPreference Stop a native command stderr line becomes a terminating error even when redirected, and the first attempt with plain redirection crashed on the untracked case. Proven both ways in scratch git repos, never against real todos: with the fix, git status --porcelain after the commit is clean and git show --stat lists both halves of the move; replaying the PRE-fix code read live from git show HEAD leaves the exact stray D entry this todo describes. A new skills/mega-todos/test-archive-batch.ps1 carries both scenarios. Approach step 3 was already satisfied by an earlier todo: skills/mega-todos/SKILL.md:453-462 passes the helper .Pathspec straight through and has no reconstruction loop left to delete. python ci/run_all.py exits 0. Known gap recorded rather than hidden: the new .ps1 test is not discovered by ci/run_all.py, which only globs tools/test_*.py, so it runs by hand until that convention changes.
