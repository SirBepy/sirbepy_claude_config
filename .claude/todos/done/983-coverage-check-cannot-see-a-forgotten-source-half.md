<!-- Claim before executing: .claude/todos/.claims/983-coverage-check-cannot-see-a-forgotten-source-half.md -->
<!-- duplicate-checked -->
<!-- checked against 978 (done/, shipped 2026-09-11) and 495 (done/). 978 built the wrapper that
     closes this at the CALL SITE by always deriving both halves; it deliberately left
     commit-pathspec.sh's own gate untouched, and its report names this as the residual. 495 is the
     original incident where a half-committed move landed; it produced the coverage-check that this
     todo is about, rather than the gap in it. -->
# The coverage check cannot see the exact mistake it exists to catch

**Type:** task
**Origin:** ai

## Goal

Make `commit-pathspec.sh`'s coverage check able to detect a forgotten source-deletion half, for a
caller who hand-assembles a pathspec instead of going through the new wrapper.

## Context

Surfaced 2026-09-11 by the builder that shipped todo 978, and proven by a test it wrote rather than
asserted. Filed by the orchestrator, since a builder does not file its own todos.

The coverage check in `skills/commit/commit-pathspec.sh` exists because of a real recurrence
(`done/495-commit-pathspec-drops-the-source-half-of-a-git-mv.md`): naming only the destination of a
move commits the copy and leaves the source deletion staged and unreported, so `git status` afterward
shows a live ` D` for a file that is not on disk.

It misses the archival case specifically, from both directions at once:

1. It inspects `git diff --cached --name-status`, so it only sees STAGED paths. An archival move is a
   raw filesystem move performed by `complete-todo.ps1`, never a `git rm`, so the source deletion is
   unstaged when `commit-pathspec.sh` runs and does not appear in that listing at all.
2. It only flags a missing path that shares a DIRECTORY with something in the pathspec. An archival
   move goes from `.claude/todos/` to `.claude/todos/done/`, which are different directories, so even
   a staged deletion would not match the shape it looks for.

Todo 978's `skills/close/archive-and-commit-todo.ps1` closes this at the call site by always deriving
both halves itself, and that is now the sanctioned path. But the gate is what protects a caller who
does not use the wrapper, and the gate is exactly what cannot see this. The run that filed this todo
hand-assembled 25 or more such pathspecs.

## Approach

1. Reproduce first. 978 already left a test in `skills/commit/test_commit_pathspec.sh` asserting that
   a destination-only pathspec leaves the source visibly pending. Start from that test rather than
   writing a new reproduction.
2. Widen what the check looks at: an unstaged working-tree deletion (`git diff --name-status` with no
   `--cached`, or `git status --porcelain`'s ` D` lines) is the signal that is currently invisible.
   Decide whether to merge both sources or to check them separately, and say why.
3. Replace the same-directory heuristic for this case. A move is identifiable by the file's own
   basename appearing as an add in one path and a delete in another, regardless of directory. Confirm
   that against the archival shape (`<id>-<slug>.md` moving into `done/`) before relying on it.
4. **Do not make this block on a shared index.** The existing check deliberately warns rather than
   refuses when an unrelated staged path appears, because blocking there would brick `/commit` for
   every concurrent session in this repo. A deletion belonging to another session's work must stay a
   warning; only a deletion that pairs with an add already in THIS pathspec is a genuine hit.
5. Keep the `--force coverage` override working exactly as it does now.

## Acceptance

- A destination-only archival pathspec is caught, with the source path named.
- Naming both halves still passes silently.
- Another session's unrelated staged or unstaged deletion still only warns, never refuses; prove this
  with a test, since it is the regression that would hurt most.
- The existing suite still passes in full, and `python ci/run_all.py` passes.

## Notes

- The wrapper from 978 is the preferred path and this todo does not replace it. This is the backstop
  for when someone does not use it.
- Resist widening the check into a general move detector. The concrete failure is one shape, and a
  broader heuristic on a shared checkout buys false positives that will get it overridden by habit.
- Fixed 2026-09-11. The check now reads git diff --name-status without --cached as a second, separate pass, because an archival move is a raw filesystem move that never touches the index, so the source deletion was invisible to the staged-only read no matter how long you looked. Move identification keeps the original same-directory rule for a real git mv and adds a same-basename match against the pathspec array itself, checked against the pathspec rather than against a diff's add side, since the archival destination is usually still untracked when the check runs. The archival basename really is identical on both halves, verified against the fixture shape rather than assumed. 978's existing destination-only test was updated rather than replaced: it now asserts refusal naming the source path with HEAD untouched, plus a force pass proving the override still works and still leaves the source visibly pending, so nothing silently fixes the caller's omission. The property protected hardest, and the one a careless fix breaks: an unrelated deletion belonging to another session still only warns and never refuses, proven by two new tests covering the staged and unstaged forms, because refusing there would stop every concurrent session in this checkout from committing. Suite went 38 cases to 45.
