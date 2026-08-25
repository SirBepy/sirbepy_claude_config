<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# 775 - Nothing stops `git stash` from swallowing a peer session's work

**Type:** skill-improvement
**Origin:** ai
Status: open

Skill: `~/.claude/skills/commit/SKILL.md` (step 8 / edge-cases.md), and possibly
`hooks/` as the enforcement point.

## Goal

Close the gap that lets a session run `git stash` in a checkout shared with a concurrent session,
temporarily removing that session's uncommitted work from disk.

## Context

Incident 2026-08-25, zng-app. A session wanted to prove a failing test was pre-existing rather than
caused by its own edits, and ran:

```
git stash push -- lib test
fvm flutter test test/widget_test.dart
git stash pop
```

`list_peers` had already reported an active peer session in the same worktree, editing
`lib/ui/loan_application/biller_landing/components/sections/hero_section.dart` and
`footer_section.dart`. The pathspec `lib` swept both of those, plus
`entity_slug_landing_screen.dart`, off disk for the duration of the test run.

It recovered cleanly - `stash pop` succeeded, the stash was dropped, and `git status` afterwards
confirmed every peer file was back - so nothing was lost. But the safety margin was luck, not
design:

- If the peer had WRITTEN to any of those files during the window, `pop` would have conflicted.
- If the test command had hung or the session had been interrupted mid-window, the peer's work
  would have sat in a stash entry the peer knew nothing about.

## Why the existing rules did not catch it

The whole concurrency doctrine is written around the INDEX and the COMMIT:

- Global `CLAUDE.md`: "Leave all changes unstaged. The main agent will run `/commit` by pathspec"
  (feedback_never_stage_leave_unstaged).
- `/commit` step 8: commit by pathspec, "never reads the index", plus a working-tree diff check.
- `/commit` step 8: "Never `git reset` or unstage entries you didn't stage".

`git stash` is none of those. It is not staging, not committing, and not `reset`. It reads the
whole working tree by pathspec and is the one common command that removes ANOTHER session's
uncommitted changes from disk. No rule names it.

## Approach

Two layers, either or both:

1. **Rule:** add `git stash` to `/commit`'s "Never" list alongside `git reset`, and to
   `skills/commit/edge-cases.md`'s shared-checkout section. State the safe alternative: to test a
   file in isolation, copy it to a scratch path or use `git stash push -- <exact files you wrote>`
   naming individual paths, never a directory.
2. **Hook:** a `PreToolUse` guard matching `git stash` (push/save, not `list`/`show`) that checks
   whether the repo has other live sessions, and refuses if the pathspec is a directory rather
   than an explicit file list. This is the layer that actually enforces it - the rule alone did
   not stop the incident, because the session was not reading `/commit` at the time.

Worth checking whether `git checkout -- <dir>`, `git restore`, and `git clean` have the same gap;
they are the same class of working-tree-wide destructive command.

## Acceptance

- `git stash push -- lib` in a repo with a live peer is refused or warns, naming the peer's files
  that would be swept.
- `git stash list` / `git stash show` are unaffected.
