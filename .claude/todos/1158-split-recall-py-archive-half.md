<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1088 splits hooks/outbound-verify-guard.py, a different file; only the word "split" is shared -->
# Split skills/recall/recall.py: move the archive half into its own module

**Type:** task
**Origin:** ai

## Goal

`skills/recall/recall.py` (723 lines at 25471a1) holds two concerns that change for different
reasons: reading (redaction, extraction, index, search/show/activity) and archiving (compress,
zip re-verify, health warnings). Split the archive half into `skills/recall/archive.py`.

## Context

Filed by `/close`'s code-check on 2026-10-08 (session eef17188), class 3: the split needs a
decision on where the shared pieces live (`SESSION_RE`, `_atomic_write`, `LOCK_STALE_SECONDS`,
`MISSING_LOG`, which `health_warnings` reads but `Index.update` writes). The file already has
section comments marking the seam: `# ---------- compression ----------` through
`_prune_empty_dirs`. The scheduled task (`register-archive-task.ps1`) invokes
`recall.py compress`, so that CLI entry must keep working.

## Approach

- `archive.py`: `compress_cutoff`, `_session_groups`, `_crc_of`, `cmd_compress`, `_compress_due`,
  `_verify_one_zip`, `_prune_empty_dirs`, `health_warnings`, plus the archive constants.
- Shared constants and `_atomic_write` either stay in `recall.py` and `archive.py` imports them,
  or move to a small `_common.py`; pick whichever avoids a circular import.
- `recall.py compress` delegates to `archive.cmd_compress`, so the registered task needs no change.

## Acceptance

- `python skills/recall/test_recall.py` passes unchanged except for import paths.
- `python skills/recall/recall.py compress --dry-run` still works, and the scheduled task's
  next `compress.log` line reads OK.
