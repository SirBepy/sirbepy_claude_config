<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Memory freshness: verified dates and superseded-by links

**Type:** task
**Origin:** dev

## Goal

A memory says when it was last verified and, when replaced, points at what replaced it, so a stale
fact is visible as stale instead of being trusted forever or silently overwritten.

## Context

Designed in `refs/permanent-memory.md` ("Freshness and supersession"), picked by Joe on 2026-10-08
in todo 95's brainstorm. Evidence: on 2026-09-10 two todos (929, 953) were scored on recorded
repros of bugs already fixed (`feedback_a_recorded_reproduction_goes_stale`). Prior art: Zep /
Graphiti keep invalidated facts with validity windows rather than deleting them (cited by the
2026-10-08 research agent, not read directly).

## Approach

- Frontmatter `verified: YYYY-MM-DD` (set on ADD/UPDATE) and `superseded_by: <name>`.
- `refs/memory-rubric.md`: a changed fact becomes UPDATE-with-supersession (old file kept, marked)
  when its history matters; DELETE stays for facts that were simply wrong.
- Superseded files drop out of `MEMORY.md`, trigger tables (1153) and `recall.py memory` results
  by default (`--all` shows them).
- `/cleanup-memory` flags tool-version quirks and reproductions whose `verified` date is old.

## Acceptance

- Rubric and `/cleanup-memory` updated; a superseded memory is excluded from loading but still on
  disk with its link.
- `/cleanup-memory` dry run on one real project lists old-`verified` candidates.
