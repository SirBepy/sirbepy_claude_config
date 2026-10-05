<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-05; grepped backlog + done/ for "tool_suffix" and "rsplit(\"__\"", no hit. -->
# Add a tool_suffix helper to _hooklib instead of a sixth copy of the MCP-name strip

**Type:** task
**Origin:** ai

## Goal
Hooks strip an MCP tool name's `mcp__<server>__` prefix through one `_hooklib.tool_suffix(name)`.

## Context
Found by the 2026-10-05 pre-push /code-check (class 2, DRY). The one-liner
`name.rsplit("__", 1)[-1] if "__" in name else name` gained two new copies in the unpushed range,
`hooks/precompact-backup.py:88-89` (`_tool_suffix`) and `hooks/testing-floor-flag.py:60`, on top of
four existing ones: `hooks/croatian-question-guard.py:76`, `hooks/em-dash-guard.py:122`,
`hooks/send-message-stop-guard.py:97`, `hooks/ui-screenshot-reminder.py:80`. Every one of those
files already imports from `hooks/_hooklib.py`.

## Approach
Add `tool_suffix(name)` to `hooks/_hooklib.py` and switch all six call sites to it. Write the
`_hooklib.py` change in one Write call: a half-written module that guards import takes shell access
from every live session.

## Acceptance
- `python ci/run_all.py` passes, including the hook import smoke check.
- `grep -n 'rsplit("__", 1)' hooks/*.py` finds only `_hooklib.py`.
