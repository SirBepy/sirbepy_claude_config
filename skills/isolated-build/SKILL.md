---
name: isolated-build
description: Build in a scratch git worktree with its own dev server while the main checkout stays untouched, then land the work onto the main branch without losing files or fighting worktree removal.
argument-hint: "[start <name>|land]"
---

# /isolated-build

> Build in an isolated worktree, then land the work onto the main branch cleanly.

Two verbs. `start` sets up the worktree and its dev server - both already solved elsewhere, so
this just sequences the existing tools. `land` is the actual reason this skill exists: getting
work out of a worktree and onto the branch without losing it, and knowing which removal failures
are expected. Read `land.ps1` (next to this file) before using `land` - it is the documentation
for that half, this file only orients you to it.

## When this applies

A multi-step build where the dev keeps the app open and testing while Claude works - a live dev
server in the main checkout would show half-finished code, or a second `npm run dev` on the same
port would collide with the one already running. Not for a quick single-file edit; `start`'s own
`npm install` cost only pays off for a real multi-step build.

## `start <name>`

1. `git worktree add ../<repo>-<name> -b feat/<name>` - a sibling directory, never inside the main
   checkout, never a `.claude/worktrees/` path (that's `EnterWorktree`'s territory, see below).
2. A REAL install in the worktree (`npm install`, not a junction to the main tree's
   `node_modules`). A junctioned `node_modules` is exactly the reparse-point hazard
   `safe-remove-worktree.ps1`'s own header describes, and separately, some dev-server configs
   (Vite's `server.fs.allow`) reject serving a path outside the project root, so a symlinked
   dependency 403s at request time instead of failing at install time.
3. Bring up the dev server per `~/.claude/skills/supervised-run/SKILL.md`, with two settings that
   matter here specifically: `-Kind ephemeral` (this entry has no reuse value once landed) and a
   PINNED port via `-NoDynamicPort` if the app persists to localStorage/sessionStorage/IndexedDB
   (those are per-origin, so a random port each restart orphans the old data). Read that skill's
   Port table for the exact `{PORT}` flag per tool - not restated here.
4. Poll for the readiness marker per the same skill's "Wait for readiness" section before using
   the port.
5. Report the id and port back. Everything from here happens in the worktree: edits, the dev
   server, verification, even a real commit if the work warrants one - `land` handles bringing
   whichever of those exist back to the main checkout.

## `land`

```
~/.claude/skills/isolated-build/land.ps1 -WorktreePath <path> -RepoRoot <main checkout> [-SupervisorId <id>] [-TargetBranch <branch>] [-DryRun]
```

Run this from (or pointed at) the main checkout once the worktree's work is verified and ready.
It does five things, in this fixed order, because the order is what the 2026-08-29 data-loss
incident and the 2026-09-07 half-removal were both caused by getting wrong:

1. MOVES screenshots (`.for_bepy/screenshots/`) and any uncommitted files out of the worktree
   FIRST, before anything that could delete them - move, not copy: leaving the original behind
   once its content is safely in the main checkout only guarantees step 4 below sees a dirty
   worktree. File deletions inside the worktree are reported, never auto-mirrored - deleting a
   file in the main checkout on the script's own say-so is exactly the kind of silent destructive
   action this skill exists to avoid.
2. Fast-forwards the main checkout's current branch onto the worktree's branch, if it has commits
   the main checkout lacks. Fast-forward only - `land.ps1` never creates a commit or a merge
   commit, so it never breaks the "helper skills and subagents never commit" rule. A diverged
   branch is reported and left alone, never force-merged or rebased.
3. Stops the supervised dev-server entry (`-SupervisorId`), best-effort - an open handle on the
   worktree directory is the most likely cause of a step-4 removal failure.
4. Removes the worktree by calling `~/.claude/skills/close/safe-remove-worktree.ps1` - never
   reimplemented here. Read that script's own header for why a naive remove is dangerous. **That
   script's plain `git worktree remove` call throws a terminating error on ANY stderr under PS
   5.1 (confirmed 2026-09-10) and never reaches its own --force/rmdir+prune fallback if the
   worktree still has uncommitted content** - step 1's move is what keeps removal on the working
   path in practice, not that fallback chain.
5. Deletes the worktree's branch, but only if removal actually finished AND step 2 confirmed its
   commits are safe on the main branch (or it had none to begin with).

**A removal failure that survives step 1's cleanup (a genuine file lock, or worktree cruft step 1
doesn't know about, e.g. build artifacts) is expected, not a bug in this skill.** `land.ps1`
reports it and leaves the directory on disk for a later manual sweep - it does not retry in a
loop, and it does not re-add the worktree to paper over it. Branch deletion is skipped in that
case, since the branch is still in use by the surviving directory.

### `-SkipRemoval`

Pass this when the worktree was created by the harness's `EnterWorktree` tool instead of step 1
above - that tool's own `ExitWorktree` owns disposal (`action: "keep"` or `"remove"`), so calling
`safe-remove-worktree.ps1` on a path it doesn't manage would fight it. Everything else in `land`
(file copy, fast-forward, server stop) still applies unchanged; only step 4 is skipped.

## `EnterWorktree`/`ExitWorktree` vs raw `git worktree`

Use the harness tools only when a dev is present in an interactive session and either says
"worktree" directly or a project's own CLAUDE.md/memory directs it - that's the documented trigger
for `EnterWorktree`, and it needs a consent disclosure the tool renders itself. Any subagent,
unattended run, or non-interactive dispatch cannot rely on it: the disclosure has no
`--permission-prompt-tool` path to render through and the call is refused outright (confirmed
2026-09-07, countoff session). Those cases use plain `git worktree add` per `start` above, no
exception. `EnterWorktree` also always branches under `.claude/worktrees/` from a config-governed
base ref, never an arbitrary sibling path - a different worktree layout, not a drop-in replacement
for `start` even when it is available.

## Notes

- `land.ps1` never commits. If the worktree carries uncommitted files, they land as uncommitted
  files in the main checkout, and the normal `/commit` flow (prefilter gate, staging by pathspec)
  runs there afterward, same as any other change.
- Both scripts refuse to act on a path `git worktree list` doesn't already recognize as
  registered - neither one will touch the main checkout by mistake.
