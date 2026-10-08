<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; done/982 fixed heredoc bodies, done/869 fixed Remove-Item target binding; neither covers the powershell -Command wrapper -->
# destructive-command-guard misses a destructive command wrapped in `powershell -Command "..."`

**Type:** task
**Origin:** ai

## Goal
A destructive command wrapped in `powershell -Command "..."` or `pwsh -Command "..."` is caught the
same way one wrapped in `bash -c "..."` already is.

## Context
Found 2026-10-08 by the loop-todos cycle 1 builder that fixed todo 982: `Remove-Item -Recurse -Force C:\`
inside `powershell -Command "..."` returns exit 0 from `hooks/destructive-command-guard.py`.
`LEADING_WRAPPER_RE` in `hooks/_destructive_guard_shared.py` unwraps only `sh|bash|zsh|dash -c`. The
`bash -c` case is now pinned by a regression test; the PowerShell wrapper has no coverage.

## Approach
Extend `LEADING_WRAPPER_RE` (or its caller) to unwrap `powershell|pwsh [-NoProfile] -Command "<cmd>"`
and `-c`, then add true-positive cases to `hooks/test_destructive_command_guard.py` plus a
false-positive case (a harmless `powershell -Command "Get-ChildItem"`). This is a live guard every
session runs: write the module in one complete edit and run the test file right after.

## Acceptance
- `powershell -Command "Remove-Item -Recurse -Force C:\"` is denied.
- `powershell -NoProfile -Command "Get-ChildItem"` passes.
- `python hooks/test_destructive_command_guard.py` passes.
