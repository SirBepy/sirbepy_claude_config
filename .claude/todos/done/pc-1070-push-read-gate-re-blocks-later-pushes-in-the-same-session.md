<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=9, reconfirm-count=1, content-hash=ff093473 -->
<!-- duplicate-checked: 467 created the gate; this is the gate re-arming after its first pass -->
# push-read-gate blocks later pushes in a session that already pushed once

**Type:** skill-improvement
**Origin:** ai

## Goal

After a session's first `git push` passes `hooks/push-read-gate.py`, every later push in that
session goes through without another read of `snippets/auto-commit.md`, as the hook's own
docstring promises (`hooks/push-read-gate.py:17-19`: "every later push in the session is
unguarded - this is a FIRST-push gate only").

## Context

Seen 2026-10-02 in the cueline `/auto-do-todos` session (sessionId
`11837434-1749-4fa2-9e97-36e7b04afbf9`):

1. First push blocked; Claude read `snippets/auto-commit.md` (full file earlier in the session, then
   a partial Read); the push to `SirBepy/cueline` then succeeded (`ba66f5a6..06fe6c71`).
2. About two hours later a bash call chaining `commit-pathspec.sh ... && git push ...` was denied
   with the same "This session's first `git push` is blocked" message. After another partial Read,
   a standalone push succeeded (`06fe6c71..60c2cfca`).
3. A third push (chained after a commit again) was denied once more; a partial Read was refused by
   the harness as "file unchanged since your last Read", yet the next standalone push succeeded
   (`60c2cfca..08dc9c33`).

UNVERIFIED cause, would check: the hook's `push-gate-passed-<session>` marker lives in
`hooks/.session-markers/` (`:40-42`), and `hooks/write-session-marker.ps1` prints "Pruned N dead
session marker(s)" when it runs; it or another pruner may delete the passed/read markers. The
chained-vs-standalone pattern may be coincidence.

## Approach

1. Reproduce: pass the gate once, run `write-session-marker.ps1` (or wait for a prune), push again.
2. If pruning removes the markers, make the pruner skip `push-gate-passed-*`/`read-auto-commit-*`
   for live sessions, or key them so liveness is checked the same way session markers are.
3. Add a self-test covering "second push after a prune is allowed".

## Acceptance

- A session that passed the gate once is never re-gated, regardless of marker pruning or chaining.

## Notes

- Duplicate of 1029 - merged during /cleanup-todos 2026-10-05; confirmed prune root cause folded into 1029's Notes.
