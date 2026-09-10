<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=8, reconfirm-count=1, content-hash=2f8eadf5 -->
<!-- duplicate-checked: grepped this backlog and done/ for "worktree" and "isolated". Nothing covers the build-and-land lifecycle; supervised-run owns servers only, and EnterWorktree is a harness tool with no skill around it. -->
# The worktree build-and-land dance has no skill, and it was hand-run three times in one session

**Type:** skill-improvement
**Origin:** ai

## Goal

Make "build this in an isolated worktree while the dev keeps using the app, then land it on main"
one command, instead of eleven hand-typed steps repeated per feature.

## Context

Surfaced in the countoff session of 2026-09-07. That project's own memory
(`build-in-a-worktree-while-joe-tests`) says to use a worktree for any multi-step build while Joe
has the app open, and gives a three-line recipe. The recipe is the easy part. The full sequence was
hand-run three times, identically, for three features in one session:

1. `git worktree add ../<repo>-<name> -b feat/<name>`
2. a real `npm install` in it, never a junction to the main tree (the memory documents why: Vite's
   `server.fs.allow` blocks paths outside the project root, so the icon font 403s)
3. `sv.ps1 ensure` a dev server on a fresh pinned port, `-Kind ephemeral -NoDynamicPort`
4. poll the supervisor log for the readiness marker
5. typecheck, build, run the project's probes against that port
6. copy the changed files back into the main checkout, by explicit hand-typed path list
7. copy `.for_bepy/screenshots/<label>/` back too, BEFORE removing the worktree
8. `sv.ps1 stop` the entry
9. `git worktree remove --force`, which fails Permission denied and leaves the directory behind
10. `git branch -D`
11. re-run the probes against the main checkout's own server, then `Remove-Item -Recurse -Force`
    the leftover directory once its handles are released

Steps 6, 7, 9 and 11 are the ones with teeth. Step 7 is a documented data-loss incident
(2026-08-29: seven screenshots destroyed by the removal). Step 9's half-failure was reproduced twice
on 2026-09-07: git drops its own bookkeeping and deletes the branch, but the directory survives, so
the state afterwards is "git thinks it is gone, disk disagrees". Step 6 by hand is how a file gets
left in the worktree and lost with it.

`EnterWorktree` was tried first and refused outright: it needs a consent disclosure the configured
`--permission-prompt-tool` cannot render, so a non-interactive session cannot use it at all. Any
skill here has to assume plain `git worktree` plus absolute paths.

## Approach

- New skill, `~/.claude/skills/isolated-build/SKILL.md`, two verbs:
  - `start <name>` covers steps 1-4 and prints the port it pinned.
  - `land` covers steps 6-11, taking the changed-file list from `git status --porcelain` run INSIDE
    the worktree rather than a hand-typed list.
- `land` copies screenshots out before it stops the server, and treats a Permission denied from
  `worktree remove` as expected: report it, carry on, and leave the directory for a later sweep
  rather than retrying in a loop or re-adding the worktree.
- It must NOT commit. Committing stays with `/commit` in the main checkout after `land` returns, per
  the global rule that helper skills and subagents never commit.
- Read `~/.claude/skills/supervised-run/sv.ps1` for the exact `ensure` flags rather than restating
  them. The port pinning (`-NoDynamicPort` plus a literal port) is load-bearing wherever the app
  persists to IndexedDB or localStorage, since those are per-origin.
- Check whether `/disk-doctor` should learn about leftover `<repo>-<name>` sibling directories, so
  step 11's residue gets reclaimed even when a session ends before the handles release.

## Acceptance

- A feature can be built and landed with two invocations and no hand-typed path list.
- Running it twice in a row leaves no stray worktree directory and no supervised entry behind.
- `git worktree list` shows only the main checkout afterwards.
- The skill's own description stays inside the ~25-word budget.

## Notes

The three countoff features it would have covered are commits `733cf80`, `bb3047d`, and the video
preload commits made at the end of that same session.
