<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=448ad180 -->
# /commit push has no path for "nothing to commit but commits are unpushed"

**Type:** skill-improvement

## Goal

`/commit push` should push when the working tree is clean but the branch is ahead of its remote.
Today the skill's wording forbids it, so following the skill literally means a `/commit push`
that does nothing while the dev sits on unpushed work.

## Context

Hit on 2026-07-22 in `~/.claude`. Joe ran `/commit push` immediately after a previous turn had
already committed everything. Working tree was clean; `master` was 38 commits ahead of
`origin/master`. `skills/commit/SKILL.md` says under `## /commit push`:

> Do not push if the commit failed or there was nothing to commit.

Read literally, that blocks the push, which is plainly not what Joe wanted. Claude pushed anyway
and said so. The rule is aimed at "the commit step errored, so don't push a broken state" and at
"no changes existed, so there is nothing new to ship" - it never anticipated a clean tree that is
still ahead of the remote. That case is common in this repo specifically, where commits pile up
across sessions and only get pushed occasionally.

Same wording is duplicated under `## /commit pushbump` and `## /commit pushnbump`
("Do not push if either commit failed or there was nothing to commit"), so all three need the
same treatment.

## Approach

In `~/.claude/skills/commit/SKILL.md`, replace the blanket rule in all three push sections with a
two-case rule:

1. The commit step FAILED (error, hook rejection, aborted by the test gate): do not push. Unchanged.
2. There was nothing to commit: do NOT stop. Check `git -C <path> status --short --branch` (or
   `git rev-list --count @{u}..HEAD`). If the branch is ahead of its upstream, push those existing
   commits and say how many were pushed. If it is ahead by zero, say "nothing to commit, nothing
   to push" and stop.

Also handle no-upstream: if `@{u}` does not resolve, say so and offer `git push -u origin <branch>`
rather than silently doing nothing.

Keep the Build watch behavior as-is: it should run after any push that actually transferred
commits, including this new path.

## Acceptance

- `/commit push` on a clean tree with unpushed commits pushes them and reports the count.
- `/commit push` on a clean tree with zero unpushed commits still stops, with a clear message.
- A failed commit still blocks the push (no regression on the original intent of the rule).
- `pushbump` and `pushnbump` carry the same corrected wording, not the old blanket one.

## Notes

- The push in the originating session succeeded (`ec2decc..e1f7ca6`), so nothing is stuck; this
  todo is purely about the skill text matching what Claude actually has to do.
- completed, commit 0796403
