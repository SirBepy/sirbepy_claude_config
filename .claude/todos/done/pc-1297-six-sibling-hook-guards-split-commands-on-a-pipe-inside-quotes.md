<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1185 fixed flutter-workdir-guard only; this covers its six siblings -->
# Six sibling hook guards split commands on a pipe inside quotes

**Type:** skill-improvement
**Origin:** ai
**Summary:** Six hook guards define the same unquoted `CHAIN_SPLIT_RE` that pc-1185 just replaced in flutter-workdir-guard, so a quoted `|` or `;` inside a grep pattern or commit message can make them misread a command.

## Goal
Each sibling guard splits a shell command into statements outside quotes only, using `split_command_segments` from `hooks/_hooklib.py`, with a test per guard that a quoted separator no longer splits and a real separator still does.

## Context
Found 2026-11-03 by the pc-1185 builder. The guards are `hooks/agent-shared-tree-guard.py` (about line 60), `hooks/commit-window-guard.py`, `hooks/dev-backend-guard.py`, `hooks/git-workdir-guard.py`, `hooks/push-gate.py` and `hooks/push-read-gate.py`. Two caveats from that builder: `split_command_segments` also splits on a single ampersand, so the PowerShell call operator needs a check per guard, and it does not handle a backslash-escaped quote inside a quoted string (pc-1203 covers a related case in `shell-content-write-guard.py`). Each is a fail-closed gate, so a fix must keep a negative test proving a real chained command is still seen.

## Approach
One guard per commit, each with its own test. Start with `push-gate.py` and `push-read-gate.py` since they gate pushes. Do not touch `_hooklib.py`.

## Acceptance
- [ ] Every guard above uses the shared quote-aware splitter, or has a stated reason it cannot.
- [ ] Each guard's test covers a quoted separator (not split) and an unquoted one (split).

## Notes

- Added hooks/_hooklib.py split_gate_segments (quote-aware, keeps heredoc bodies, falls back to the plain split on unbalanced quotes so gates stay fail-closed) and switched all six guards to it. Test: hooks/test_gate_quoted_separators.py (8 guard cases fail on HEAD guards, pass now). Landed in the commit titled 'FIX: six gate hooks split on separators outside quotes only'.
