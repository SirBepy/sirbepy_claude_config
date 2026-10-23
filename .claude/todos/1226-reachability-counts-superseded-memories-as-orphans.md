<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1156 (done) added superseded_by:; no backlog file covers reachability.mjs -->
# cleanup-memory's reachability.mjs counts superseded memories as orphan files

**Type:** skill-improvement
**Origin:** ai

## Goal

A memory file carrying `superseded_by:` frontmatter is never reported as `orphan-file` by
`skills/cleanup-memory/reachability.mjs`, so `/cleanup-memory` needs no manual subtraction.

## Context

Todo 1156 (completed 2026-10-23, loop-todos cycle 1) made superseded memories stay on disk with no
`MEMORY.md` index line, by design. Its builder could not edit `reachability.mjs` (off limits for that
dispatch), so `skills/cleanup-memory/SKILL.md` Step 2 now documents a manual subtraction of
superseded files from the `orphan-file` count. A rule that relies on a manual subtraction gets skipped.

## Approach

In `reachability.mjs`'s `collectFiles` (or wherever `orphan-file` is computed), read each file's
frontmatter and classify a file with `superseded_by:` as `superseded` instead of `orphan-file`; print
that count separately. Remove the manual-subtraction sentence from `SKILL.md` Step 2. Add a scratch
temp-dir check (one live, one superseded, one true orphan) and run it.

## Acceptance

- A superseded file reports as `superseded`, never `orphan-file`; a true orphan still reports as one.
- `SKILL.md` Step 2 no longer asks for a manual subtraction.
