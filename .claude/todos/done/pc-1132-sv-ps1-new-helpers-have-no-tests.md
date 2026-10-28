<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; no live or done todo covers sv.ps1 tests -->
# sv.ps1's new param and status helpers shipped without tests

**Type:** task
**Origin:** ai

## Goal
`skills/supervised-run/sv.ps1`'s pure helpers have a self-test that runs in `ci/run_all.py`.

## Context
Loop-todos cycle 1 (2026-10-08, commit cd38107, todos 1116 and 1118) added `Get-ParamsHash`
(parses repeatable `-Param name=value`), `Format-StartedAt` (epoch millis to a UTC string),
`Get-ApiErrorBody` and the started vs reused-running branch to `sv.ps1`. None has a test, though
CLAUDE.md's testing floor says each behaviour change ships with a test that fails without it. The
cycle's /code-check flagged it. `Get-ParamsHash` and `Format-StartedAt` are pure functions with no
server dependency. The one tested `.ps1` precedent is `skills/mega-todos/test-archive-batch.ps1`.

## Approach
Dot-source or extract the pure helpers so a test can call them without running the CLI, write a
`test_sv.ps1` (or a Python wrapper that shells out to PowerShell, if that is how `ci/run_all.py`
discovers skill-script tests) covering: one and several `-Param` values, a value containing `=`, a
malformed entry, and `Format-StartedAt` on a known epoch.

## Acceptance
- The new test fails if `Get-ParamsHash` drops the second `-Param`, and passes now.
- `python ci/run_all.py` discovers and passes it.

## Notes

- Pure helpers moved into skills/supervised-run/sv-lib.ps1 (dot-sourced by sv.ps1, whose diff is only the removed bodies plus one dot-source line); test_sv.ps1 covers one/several -Param, a value with '=', malformed entry, Format-StartedAt and Get-ApiErrorBody; dropping the second -Param makes it fail. ci/run_all.py's skill-test discovery now runs .ps1 tests via powershell -File.
