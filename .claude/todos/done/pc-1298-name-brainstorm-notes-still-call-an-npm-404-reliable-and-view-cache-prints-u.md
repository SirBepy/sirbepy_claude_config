<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1259 fixed the checker code; this is the notes file and a cache letter it left behind -->
# name-brainstorm checker-notes.md still calls an npm 404 reliable, and view-cache prints U for UNKNOWN

**Type:** skill-improvement
**Origin:** ai
**Summary:** After pc-1259 an npm 404 reports UNKNOWN, but `skills/name-brainstorm/checker-notes.md` lines 27 and 30 still describe the old semantic, and `view-cache.mjs` would print `U` where its header comment promises `?`.

## Goal
`checker-notes.md` matches the checker's real npm behaviour, and `view-cache.mjs` and its header comment agree on the letter for UNKNOWN.

## Context
Found 2026-11-03 by the pc-1259 builder. Line 27 says npm is "reliable for the exact name only" and line 30 says only 429, 5xx and timeouts give UNKNOWN; both predate the change where a 404 means "free or unpublished". `view-cache.mjs` takes the first letter of the status, so a cached UNKNOWN prints `U`; the todo's own note says UNKNOWN is never cached today, so this is latent.

## Approach
Reword the two lines in `checker-notes.md`. In `view-cache.mjs` either map UNKNOWN to `?` or fix the comment. Extend `skills/name-brainstorm/test_view_cache.cjs`.

## Acceptance
- [ ] `checker-notes.md` states that an npm 404 is UNKNOWN with the note "free or unpublished".
- [ ] `view-cache.mjs` and its comment agree, with a test.

## Notes

- view-cache.mjs now prints ? for UNKNOWN (was U); checker-notes.md states an npm 404 is UNKNOWN with the note "free or unpublished". test_view_cache.cjs fails on the old script (red-proved via VIEW_CACHE_PATH).
