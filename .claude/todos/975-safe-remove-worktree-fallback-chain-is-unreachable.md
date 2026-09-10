<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/970 built skills/isolated-build around this script and worked AROUND
     this bug rather than fixing it, because skills/close/*.ps1 was off limits to that dispatch;
     no existing todo covers the script's own error handling -->
# `safe-remove-worktree.ps1`'s documented fallback chain can never run

**Type:** bug
**Origin:** ai

## Goal

Make `skills/close/safe-remove-worktree.ps1` actually reach its own `--force` and `rmdir` fallbacks,
which today are dead code on the most common failure path.

## Context

Found and reproduced 2026-09-10 by the builder that closed
`done/970-the-worktree-build-and-land-dance-has-no-skill.md`.

The script calls plain `git worktree remove`, pipes it through `2>&1`, and runs under
`$ErrorActionPreference = 'Stop'`. In Windows PowerShell 5.1 that combination turns ANY stderr line
from a native executable into a terminating `NativeCommandError`, even when git exits 0 and even
when the message is entirely ordinary. Reproduced directly:

```
git.exe : fatal: '<path>' contains modified or untracked files, use --force to delete it
    + CategoryInfo : NotSpecified: (...) [], NativeCommandError
```

That message is git's normal, expected response to a worktree with uncommitted content, and it is
precisely the case the script's `--force` fallback exists to handle. Because the error terminates
first, the fallback chain (`--force`, then `rmdir /S /Q`, then `git worktree prune`) is never
reached. So the script's own documented recovery is unreachable exactly when it is needed.

This is the same PowerShell trap the tool documentation already warns about in general terms:
redirecting a native command's stderr inside PowerShell wraps each line in an ErrorRecord and sets
`$?` to false even on exit code 0.

**Why this was worked around rather than fixed:** `skills/close/*.ps1` was off limits to that
dispatch, because the orchestrator was calling `complete-todo.ps1` and `claim-todo.ps1` continuously
while it ran. `skills/isolated-build/land.ps1` therefore uses move-not-copy semantics so the worktree
is git-clean before removal is attempted, which sidesteps the most common trigger. A genuine
permission-denied lock, or unrelated cruft in the worktree, still hits the unreached fallback.

## Approach

1. Reproduce it first, so the fix is verified against the real failure and not a guess: create a
   scratch worktree, leave an untracked file in it, and call the script.
2. Stop treating native stderr as terminating. The usual shapes are capturing output without `2>&1`
   and branching on `$LASTEXITCODE`, or wrapping the call in `try/catch` with the redirect removed.
   Pick one deliberately and say in a comment why, since this is the second time this class of trap
   has bitten this repo.
3. Re-verify every fallback in the chain individually, not just the happy path: a worktree with
   untracked content must reach `--force`, and a locked path must reach the `rmdir` step.
4. Do not weaken the safety property the script exists for. It must still refuse to follow a reparse
   point or symlink out of the worktree, which is the data-loss incident behind it.

## Acceptance

- A worktree containing an untracked file is removed successfully by the script, via the `--force`
  fallback, with the path taken visible in its output.
- The reparse-point refusal still holds, proven by a test case.
- `python ci/run_all.py` exits 0.

## Notes

- Read `done/970`'s notes and `skills/isolated-build/land.ps1` first: the workaround there is
  deliberate and should stay even after this is fixed, since move-not-copy is the right behaviour
  independently.
- Related but not the same: `refs/shell-io-gotchas.md` collects PowerShell string and IO traps. This
  one belongs there too once fixed.
