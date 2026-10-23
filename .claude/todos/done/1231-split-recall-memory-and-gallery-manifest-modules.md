<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Consider splitting recall.py's memory/digest half and build_gallery.py's manifest half

**Type:** refactor
**Origin:** ai

## Goal

`skills/recall/recall.py` and `skills/preview/build_gallery.py` stay readable as they grow.

## Context

Found by the 2026-10-23 loop-todos cycle-1 `/code-check` over `8347382..HEAD`. `recall.py` is now
977 lines, ~250 of them digest and memory commands (`cmd_digest_save`, `cmd_decisions`,
`parse_memory`, `cmd_memory`, `cmd_memory_stale`) beside the transcript index; `build_gallery.py` is
524 lines with a ~190-line manifest builder beside the flat gallery. Borderline: both are
single-entry CLIs whose tests import them by path, and todo 1158 (split recall.py's archive half)
was archived as churn.

## Approach

If worth it: move the seams to `recall_memory.py` and `gallery_manifest.py`, keeping the CLI entry
points and test imports working.

## Acceptance

Both test suites pass unchanged except imports.

## Notes

- Archived by /loop-todos cycle 2 on 2026-10-23 as churn (worth 3): a behavior-neutral file split of two single-entry CLIs whose tests import them by path; todo 1158 (split recall.py's archive half) was archived for the same reason. The todo itself called it borderline.
