<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- checked against 975 (done/, fixed 2026-09-11). 975 is the PS 5.1 terminating-error trap that
     made the fallback chain unreachable; this is a different failure that only became visible once
     that chain could run at all. Same file, different defect, and 975's fix does not address it. -->
# A partly-succeeded force removal leaves a worktree this script can never clean up again

**Type:** task
**Origin:** ai

## Goal

Give `safe-remove-worktree.ps1` a way to finish the job when `git worktree remove --force` has
already unregistered a worktree but failed to delete its files.

## Context

Found 2026-09-11 while verifying todo 975's fix. It was only observable because that fix made the
fallback chain reachable for the first time, so this has probably been latent for as long as the
script has existed.

Observed directly on a throwaway worktree with a file held open under an exclusive lock:

1. `git worktree remove --force <path>` fails to delete the locked file and reports
   `error: failed to delete ... Invalid argument`.
2. It nevertheless removes the worktree from `git worktree list`.
3. The directory is still on disk, with contents.

The script's own registration guard (`skills/close/safe-remove-worktree.ps1`, the refusal that only
acts on a path `git worktree list` already knows about) now refuses that path forever. The refusal is
correct in isolation: it exists so the script can never be pointed at an arbitrary directory that
happens to contain reparse points, which is the guard protecting against the 2026-07-31 data-loss
incident. But its precondition and the leftover state are mutually exclusive, so the one tool built
to clean this up safely is the one tool that cannot.

The leftover then has to be deleted by hand, which is exactly the unguarded recursive delete the
script exists to stop anyone reaching for.

## Approach

1. Reproduce it first, deliberately: create a worktree, hold a file in it open with an exclusive
   lock, run the force path, and confirm the unregistered-but-present state. Do not build on this
   description alone.
2. Decide how the script recognises the state without weakening the registration guard. The guard's
   real purpose is "git vouched for this path", and a path that git vouched for a moment ago is not
   the same as an arbitrary directory. Candidate signals, to be checked rather than assumed: a
   `.git` file inside the leftover still pointing into the parent's `worktrees/` admin dir, or a
   surviving entry under `<repo>/.git/worktrees/` that `prune` has not yet cleared.
3. Only when such a signal is present, allow the reparse-point scan and the recursive-delete
   fallback to run against the leftover. The reparse-point refusal must still fire first and must
   still be able to abort the whole thing. Do not add a `-Force` style override that skips it.
4. If no signal survives that distinguishes a leftover from an arbitrary directory, do NOT widen the
   guard. Report that instead, and make the script print the exact manual steps plus the reason it
   will not act, so the state is at least diagnosable.

## Acceptance

- The unregistered-but-present state is reproduced before any fix is written.
- Either the script cleans up that state, or it explains it and refuses; a silent unchanged refusal
  is not acceptable either way.
- The registration guard still refuses an arbitrary directory containing reparse points, proven with
  a real directory, not by reading the code.
- The reparse-point refusal still fires before any deletion, proven the same way.
- `python ci/run_all.py` passes.

## Notes

- Weakening the registration guard is the obvious wrong answer here. It is the reason this script
  exists rather than a plain recursive delete, and the incident behind it was real data loss.
- Related: `ci/run_all.py` discovers no tests under `skills/close/`, so there is currently no way to
  land a regression test for any of this. That gap is worth naming in whatever fix lands, and may be
  worth its own todo about widening CI discovery.
