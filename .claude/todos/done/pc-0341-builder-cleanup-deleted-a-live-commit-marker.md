<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# A builder's temp-file cleanup deleted the orchestrator's live commit-guard session marker

**Type:** skill-improvement
**Origin:** ai

## Goal

Make it impossible for a subagent's own cleanup to delete a marker file another live session
depends on, so a builder finishing tidily cannot block its orchestrator's next commit.

## Context

Happened 2026-08-15 during an `/auto-do-todos` run, first-hand.

The builder executing todo 335 exercised `hooks/commit-guard.py` by hand, which required writing
marker files into `hooks/`. Its report ends "No leftover test marker files." The orchestrator's
next `git commit` was then rejected:

```
[commit-guard] Raw `git commit` is blocked; no part of this call ran...
```

`ls hooks/.commit-marker-session-*` came back empty. The orchestrator's session marker,
`hooks/.commit-marker-session-<session-id>`, written once at the start of the run per
`skills/commit/SKILL.md`, was gone. The guard itself was fine: its session-marker branch was
untouched by the refactor and all hook suites passed. The marker had simply been swept up by a
glob-shaped cleanup of `hooks/.commit-marker-*`.

Cost was small this time (rewrite the marker, retry) because the orchestrator recognised the
symptom immediately. A session that did not would read it as "the commit guard is broken" and
could plausibly reach for `CLAUDE_COMMIT_HOOK_BYPASS=1`, which is the actually dangerous outcome.

Note the marker is deliberately never consumed and is keyed per session, so nothing in the normal
lifecycle should ever remove one that is not yours.

## Approach

Two independent layers, either useful alone:

1. **Dispatch side.** `refs/delegation-doctrine.md`'s canonical builder preamble gains a line:
   clean up only the exact temp files you created, by name, never by glob, and never touch
   `hooks/.commit-marker-*`. The run that hit this had to add that line by hand to later
   dispatches, which is the sign it belongs in the copy-verbatim block.
2. **Storage side, stronger.** Move session markers out of the same directory and naming space as
   the short-lived per-commit markers, so a glob over one cannot reach the other. Check what
   `hooks/_hooklib.py`'s `oldest_fresh_marker` and `consume_fresh_marker` assume about layout
   before moving anything, and keep `exclude_prefix` working.

Prefer doing both. Layer 1 is a one-line edit; layer 2 is what makes the failure unreachable rather
than merely discouraged.

## Acceptance

- A builder that deletes every file matching `hooks/.commit-marker-*` no longer breaks a
  concurrent session's ability to commit.
- `hooks/commit-guard.py`, `pr-guard.py` and `shortcut-create-guard.py` behave identically before
  and after, proven by their test suites plus a by-hand allow/block exercise of the two that have
  no suite.
- The preamble line is present in the copy-verbatim block, not just in prose elsewhere.

## Notes

- Done 2026-08-16, commit 8a55286. Both layers shipped. Layer 1: the canonical builder preamble now bans glob cleanup by name, naming hooks/.commit-marker-* and hooks/.session-markers/ explicitly. Layer 2 was judged safe after reading _hooklib.py first: oldest_fresh_marker and consume_fresh_marker already glob non-recursively within an arbitrary marker_dir, so session markers moved to hooks/.session-markers/<session_id>, a directory a non-recursive glob cannot reach at all. Zero _hooklib.py changes needed. All 6 live session markers were migrated, a permanent read-only legacy fallback covers stragglers, and the orchestrator's own marker was proven still working by the commit that landed this change. Also trimmed two paragraphs the doctrine still duplicated from builder-preamble.md.
