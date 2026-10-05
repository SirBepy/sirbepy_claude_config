<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /commit's baseline worktree can't be removed once the harness moves cwd into it

**Type:** skill-improvement
**Origin:** ai

## Goal

`/commit` step 6's baseline comparison (`git worktree add --detach <tmp-dir> HEAD`, run the suite, remove it) should clean up reliably on Windows. Today the removal step fails if the harness has switched the session's working directory into the new worktree.

## Context

Seen 2026-10-05 in a zng-biller session committing to `~/.claude` (b5ab1be). The sequence:

1. `git worktree add --detach C:/tmp/claude-baseline HEAD` succeeded, and the harness immediately reported "Primary working directory: C:\tmp\claude-baseline ... This is a git worktree". Every later PowerShell/Bash tool process then started with that directory as its OS cwd.
2. `safe-remove-worktree.ps1 -WorktreePath C:/tmp/claude-baseline -RepoRoot C:/Users/tecno/.claude` first failed with "contains modified or untracked files" (the CI run's `__pycache__` dirs plus files copied in for the comparison). After reverting those, it failed with `error: failed to delete 'C:/tmp/claude-baseline': Permission denied`. A `Set-Location` inside the command did not help: PowerShell's `Set-Location` does not change the process's OS cwd, which still held the directory handle.
3. git had already unregistered the worktree, so a retry got "is not a worktree registered ... refusing". `Remove-Item` on the now-empty dir failed with "in use" until the harness moved the primary cwd back to the project, later in the session.

`skills/commit/SKILL.md` step 6 says "then `git worktree remove <tmp-dir> --force`", but `refs/builder-preamble.md` says to use `safe-remove-worktree.ps1` instead. Neither mentions the cwd trap.

## Approach

- In `skills/commit/SKILL.md` step 6 (baseline comparison), add one line: before removing the baseline worktree, move the process cwd out with `[System.IO.Directory]::SetCurrentDirectory('<repo root>')` in the same PowerShell call (a plain `Set-Location` is not enough), and point at `safe-remove-worktree.ps1` instead of a bare `git worktree remove --force`, to match `refs/builder-preamble.md`.
- Optionally teach `safe-remove-worktree.ps1` to detect `Permission denied` from an already-unregistered worktree, print "directory still held by a process cwd, move cwd out and Remove-Item the empty dir" instead of the generic refusal, and accept a path git no longer lists when it is empty.

## Acceptance

- Following step 6 as written creates and removes a baseline worktree from a session whose primary cwd the harness moved into it, with no leftover directory.
- `python ci/run_all.py` passes.
