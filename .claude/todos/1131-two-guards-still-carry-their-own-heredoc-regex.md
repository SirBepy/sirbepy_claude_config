<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; done/982 added the destructive-guard copy, done/476 the shell-content-write-guard one; no live todo centralises them -->
# Two guards still carry their own heredoc-stripping regex instead of `_hooklib`'s

**Type:** task
**Origin:** ai

## Goal
One heredoc / here-string body regex for every shell guard, so the next heredoc edge-case fix lands
once.

## Context
The loop-todos cycle 1 /code-check (2026-10-08) found three near-identical heredoc-stripping regexes.
That cycle moved one into `hooks/_hooklib.py` as `HEREDOC_BODY_RE`, `HERESTRING_BODY_RE` and
`split_command_segments()`, now used by `unbounded-scan-guard.py` and `shortcut-raw-write-guard.py`.
Two copies remain:
- `hooks/_destructive_guard_shared.py` `HEREDOC_RE` / `strip_heredoc_bodies()` (added by todo 982,
  its own docstring says it generalises the next one).
- `hooks/shell-content-write-guard.py` `HEREDOC_RE` (todo 476), which deliberately keeps UNQUOTED
  heredoc bodies in scope for its own reason (variable expansion writes content), so it may need a
  quoted-only variant rather than the shared one. Read its docstring before changing it.

## Approach
Point `_destructive_guard_shared.py` at `_hooklib.HEREDOC_BODY_RE` (same semantics: quote optional).
For `shell-content-write-guard.py`, either add a quoted-tag-only variant to `_hooklib` or leave it
and document why it differs. Both are live guards every session runs: one complete edit per file,
run the matching test file right after.

## Acceptance
- `grep -n "HEREDOC" hooks/*.py` shows one definition in `_hooklib.py` (plus a documented variant if
  shell-content-write-guard keeps its own).
- `python hooks/test_destructive_command_guard.py` and `python hooks/test_shell_content_write_guard.py`
  pass.
