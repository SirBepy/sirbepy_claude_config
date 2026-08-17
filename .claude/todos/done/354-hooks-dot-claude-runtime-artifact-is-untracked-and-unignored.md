<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# `hooks/.claude/last-session-status.json` sits untracked and unignored, showing up in every `git status`

**Type:** task
**Origin:** ai

## Goal

Decide whether `hooks/.claude/` is runtime state or content, then either gitignore it or track it,
so it stops appearing as an untracked directory in every `git status` of this repo.

## Context

Observed 2026-08-16 during an `/auto-do-todos` run. `git status --short` in `~/.claude` shows:

```
?? hooks/.claude/
```

The directory contains exactly one file, `hooks/.claude/last-session-status.json`. It has never been
committed and nothing ignores it.

It looks like runtime state written by a hook, most likely `hooks/status-marker-guard.py`, but that
is UNVERIFIED: nobody has read the writer to confirm which hook creates it, what it holds, or
whether anything reads it back. Confirm the writer before deciding.

Why it is worth fixing rather than ignoring by eye: this repo's `/commit` procedure commits strictly
by pathspec and requires checking the file list against `git status`, so a permanent untracked entry
is noise in the one output that is supposed to be scanned carefully. It is also the shape of thing
that gets swept into a commit by accident by any writer that reaches for `git add -A`.

## Approach

1. Find the writer: grep `hooks/` for `last-session-status` and read whichever hook produces it.
2. Decide from what it holds:
   - **Per-session runtime state** (the likely answer): add `hooks/.claude/` to `.gitignore`,
     alongside the existing `.claude/todos/.claims/` and `.claude/todos/*-.reserved` entries, which
     are the same category.
   - **Content another session or skill depends on**: track it, and say in the hook's own file why.
3. If the file turns out to be dead (written, never read), delete the writer's write rather than
   ignoring a file nobody uses.

## Acceptance

- `git status --short` in `~/.claude` is clean of `hooks/.claude/` on a fresh session.
- The decision is recorded where the next reader will find it, not just in the `.gitignore` diff.

## Notes

- Filed 2026-08-16 by `/auto-do-todos` from its own observation, not a builder report.
- Small. Good candidate for a batch run rather than a session of its own.
- Done 2026-08-17: gitignored hooks/.claude/. Writer hunt came back empty - grepping hooks/ for last-session-status, session_status and checkedAt found NO producer anywhere in this repo, and the single file (95 bytes, {checkedAt, ok, codegen, manifests}, mtime 2026-08-14) has not changed since. Treated as a status cache written by a tool that ran with cwd=hooks/. Left the file in place rather than deleting it, since deleting a file with an unidentified writer buys nothing the ignore does not; the reason is recorded as a comment in .gitignore. Verified: git check-ignore matches, and git status --short no longer lists hooks/.claude/.
