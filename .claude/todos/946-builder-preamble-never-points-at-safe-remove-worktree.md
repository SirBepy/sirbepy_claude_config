<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=9, reconfirm-count=1, content-hash=1c539201 -->
<!-- duplicate-checked: grepped refs/, skills/ and CLAUDE.md for "safe-remove-worktree" - the only hit is the script's own file. No todo covers wiring it into a dispatch path. -->
# The builder preamble never points at safe-remove-worktree.ps1, and the junction hazard recurred

**Type:** task
**Origin:** ai

## Goal

Make a subagent that creates a git worktree learn about `safe-remove-worktree.ps1` before it removes
one, instead of reaching for `git worktree remove --force` and gutting the main checkout.

## Context

`skills/close/safe-remove-worktree.ps1` exists precisely for this. Its own docstring cites the
2026-07-31 incident (memory `worktree-removal-junction-hazard`): PS 5.1 `Remove-Item -Recurse` and
`git worktree remove --force` both follow reparse points found INSIDE a worktree, so a worktree that
junctions something back to the main checkout gets its junction followed and the MAIN checkout's
files deleted. That incident gutted two `node_modules` trees plus a `.env.local`.

**It happened again on 2026-09-05**, in a `/mega-todos` builder in `server_supervisor`. The builder
needed a clean tree to verify its own split in isolation while four other agents held uncommitted
work, so it created a scratch worktree and `mklink /J`-ed `vendor/tauri_kit` into it so cargo could
resolve the submodule. `git worktree remove --force` then followed that junction and deleted the
real submodule's contents in the shared main checkout; `git submodule status` showed it as
uninitialized. The builder noticed, ran `git submodule update --init --recursive`, and restored it
to the correct commit before any other lane's build was affected. It flagged the whole thing in its
own report, which is the only reason this is known.

Verified 2026-09-05: `grep -rl "safe-remove-worktree"` across `refs/`, `skills/` and `CLAUDE.md`
returns exactly one file, the script itself. Nothing references it. Meanwhile
`refs/builder-preamble.md`'s static block DOES tell builders to use `git worktree add` as the
sanctioned way to get a clean tree ("use `git worktree add` to a scratch path instead - never a
stash or reset on the shared tree"), so the preamble actively routes builders into the hazard and
then says nothing about getting back out.

## Approach

The removal half is the gap, not the creation half. Options:

- Add one sentence to `refs/builder-preamble.md`'s static block, right after the existing
  `git worktree add` clause, naming `~/.claude/skills/close/safe-remove-worktree.ps1` as the only
  sanctioned way to remove it and stating why `git worktree remove --force` is not. Cheapest, and it
  lands in every dispatch automatically since the block is pasted verbatim.
- Also worth considering: the builder only needed the junction because the worktree could not resolve
  a git submodule. If there is a cleaner recipe for "scratch worktree in a repo with a submodule",
  that is the fix one level up, and the preamble should carry it instead of a warning about cleanup.

Whichever is chosen, check whether `hooks/` can catch a raw `git worktree remove` the way the commit
guard catches a raw `git commit`. A prose rule in the preamble has been observed to fail before
(todo 290: a rule stated verbatim in every dispatch was broken three times in the same run).

## Acceptance

- A builder that creates a worktree is told, in the pasted preamble, how to remove it safely.
- The decision about a hook is made explicitly, not left implicit, and written down either way.

## Notes

Filed 2026-09-05 by `/mega-todos` running in `server_supervisor`, from a builder's own report-back.
This is global-tree work, so it is filed here rather than in the surfacing project's backlog.
Related: `refs/builder-preamble.md`, `skills/close/safe-remove-worktree.ps1`, memory
`worktree-removal-junction-hazard`.

**Third recurrence, 2026-09-05 13:00, hubbub autopilot session, and the ORCHESTRATOR did it, not a
builder.** Different vector, same hazard class: `git worktree add --detach C:/tmp/mg-baseline HEAD~1`
in `hubbub-game-music-guesser`, then `cp -r node_modules` into the worktree (that repo pins the
platform as `link:../hubbub/packages/*`, materialised as absolute symlinks under
`node_modules/@hubbub/`), then `rm -rf C:/tmp/mg-baseline` from the Bash tool. MSYS `rm -rf` followed
the copied symlink and emptied the real `hubbub/packages/protocol` (18 tracked files) and, through
that package's own `node_modules` links, hubbub's root top-level `node_modules` entries
(`typescript`, `turbo`, `vitest`, `.bin`). Recovered with `git checkout -- packages/protocol` and a
21-minute forced corepack reinstall (a plain reinstall said "Already up to date" and re-linked
nothing). The destructive-command guard did not fire: the target was a `C:/tmp` path. So the fix
here is not only "point builders at the helper": (a) the preamble's "use `git worktree add`" line
needs a matching "remove it with `safe-remove-worktree.ps1`, never `rm -rf`" line, and (b) an
explicit ban on copying a `node_modules` that holds `link:`/`workspace:` packages into a worktree.
Vault note: `Git Bash rm -rf follows pnpm link symlinks.md`.
