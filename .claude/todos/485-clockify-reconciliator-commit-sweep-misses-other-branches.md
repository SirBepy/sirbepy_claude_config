<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# clockify-reconciliator's commit sweep misses branches not checked out in any worktree

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix `skills/clockify-reconciliator/SKILL.md` step 6 ("Read commits") so it
sees every commit the dev made in the window, not just commits reachable from
whatever branch happens to be checked out.

## Context

Found 2026-08-22 running the skill against revaire-mobile (2 worktrees: main
on one branch, `.claude/worktrees/rev-5312` on another). Step 6 currently
says: `git -C <repo> log --author=... --since=... --until=...` with no
`--all`. Plain `git log` walks only the current branch's ancestry, so a
commit on a THIRD local branch that neither worktree had checked out
(`rev-4810-fallback-clone-approach`, `rev-139-fix-oauth-...`) was invisible.

This produced a real, dev-caught miss: the run reported zero commits for a
day that actually had three, on two branches nobody had checked out. The dev
asked "are you sure you researched all of my work?" before it was caught.
`git worktree list` alone does not fix this either - it only shows CURRENTLY
CHECKED OUT branches, and branches with real commits routinely sit
uncheckout in between sessions.

## Approach

Add `--all` to every `git log` invocation in step 6 (both the main window
pass and the late-night-spillover pass). `--all` walks every local ref
(branch, not just HEAD), so it sees commits on any branch in the repo
regardless of which one is currently checked out in which worktree, without
needing to enumerate worktrees at all. Author filtering still applies via
`--author`, so this doesn't pull in teammates' commits, just widens which of
the dev's OWN branches get checked.

## Acceptance

- Step 6's git log commands include `--all`.
- A repo with a branch not checked out anywhere is still fully covered.
- Note added to step 6 explaining why `--all` is required (not just
  `git worktree list`), so a future edit doesn't quietly drop it.

## Notes

Related, found in the same session, filed separately since it's a different
kind of gap: [[486-clockify-reconciliator-weekly-target-scope-ambiguous]] (a
stated hour target's scope - Mon-Fri vs whole week - needs confirming before
building toward it).
