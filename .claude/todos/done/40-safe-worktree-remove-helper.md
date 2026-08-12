<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# Build a safe-worktree-remove helper so junction traversal can't repeat

**Type:** skill-improvement

## Goal

Make worktree removal a one-call, junction-safe operation instead of ad-hoc `git worktree remove
--force` / `Remove-Item -Recurse`, which on 2026-07-31 recursed through a `node_modules` junction
and its inner `@fibo/ui` symlink into the MAIN checkout - deleting frontend/ui sources, gutting
two node_modules trees, and removing frontend2/.env.local (all recovered, see memory
`worktree-removal-junction-hazard`).

## Context

Fibo worktrees deliberately junction `node_modules` to the main checkout's (memory
`fibo-worktree-node-modules-junction`), and npm workspaces add symlinks like
`frontend/node_modules/@fibo/ui -> frontend/ui`. PS 5.1 `Remove-Item -Recurse` follows reparse
points; `git worktree remove --force` also proved unsafe in this configuration. 11+ worktrees were
removed manually this session, each needing the same 3-step dance.

## Approach

A small PowerShell script (e.g. `~/.claude/skills/close/safe-remove-worktree.ps1` or a standalone
skill) that takes a worktree path and: (1) lists all reparse points under it
(`Get-ChildItem -Recurse -Attributes ReparsePoint`), (2) removes each with non-recursive
`cmd /c rmdir`, (3) runs `git worktree remove` (plain, then `--force` fallback, then
`cmd /c rmdir /S /Q` for long-path failures + `git worktree prune`), (4) finishes with
`git status --short` in the main checkout and prints it. Then reference the script from the
relevant memories so future sessions reach for it instead of raw removal.

## Acceptance

- Removing a worktree that contains a junction into the main checkout leaves the main checkout's
  `git status` clean, proven by the script's own final check.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 192; renumbered to 40 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Implemented 2026-08-08: `skills/close/safe-remove-worktree.ps1` created (WorktreePath/RepoRoot/DryRun params, refuses a nonexistent path, the main checkout itself, or any path not in `git worktree list --porcelain`; unlinks reparse points non-recursively before removal; plain remove -> --force -> rmdir+prune fallback; prints final `git status --short`). Tested against a scratch repo with a real junction: all three refusals fire, DryRun reports the junction and touches nothing. No in-repo call sites reference worktree removal to update; the memories this todo names (`worktree-removal-junction-hazard`, `fibo-worktree-node-modules-junction`) live in the fibo project's own memory store, out of this global repo's scope - referencing the new script there is a fibo-project follow-up, not done here.
