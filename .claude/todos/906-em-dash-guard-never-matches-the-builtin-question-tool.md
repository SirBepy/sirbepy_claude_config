<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 350 was MCP text args, 506 was the turn-boundary scan, 892 was PreToolUse timing, 308 was bare questions. None touches the tool-NAME spelling gap. -->
# em-dash guard never matches the built-in AskUserQuestion tool name

**Type:** task
**Origin:** ai

## Goal

Make `hooks/em-dash-guard.py` cover the built-in `AskUserQuestion` tool, not just the MCP
`*ask_user_question` variant, so an em dash in a built-in question card is caught like one in a
chat message.

## Context

Found 2026-09-04 by the builder for todo 886 while adding `hooks/croatian-question-guard.py`, which
had to write its own matcher precisely because the existing one did not cover both spellings.

`hooks/em-dash-guard.py:52` keys its field map off the snake_case `ask_user_question` only, and
`settings.json`'s matcher does the same. The harness ships TWO question tools with different names:
the built-in `AskUserQuestion` (PascalCase) and `mcp__cc_conductor__ask_user_question`. Only the
second is matched, so em-dash text in a built-in question card bypasses the guard in both its
PreToolUse arm (todo 892, commit `fbb699b`) and its Stop arm.

Distinct from the earlier em-dash todos, all now in `done/`: 350 widened the guard to MCP tool text
args, 506 fixed the turn-boundary scan, 892 moved it to PreToolUse so it denies before delivery.
This one is purely about which tool NAMES the matcher recognises.

`hooks/croatian-question-guard.py` (commit `c5ed7c1`) already carries a matcher covering both
spellings - copy its shape rather than deriving a new one.

## Approach

1. Add the PascalCase `AskUserQuestion` name to the field map with the same fields the MCP variant
   uses. Confirm the built-in's payload really uses those key names first; do not assume it mirrors
   the MCP one.
2. Widen `settings.json`'s PreToolUse matcher the way `croatian-question-guard.py`'s is written.
3. Add a test case per arm to `hooks/test_em_dash_guard.py` pinning a built-in-shaped payload.

## Acceptance

- A built-in `AskUserQuestion` payload carrying an em dash is denied at PreToolUse.
- The MCP variant behaves exactly as it does today; the existing 24 cases stay green.
- `python ci/run_all.py` exits 0.

## Notes

- Filed by /mega-todos on 2026-09-04 from a wave-1 builder's out-of-scope report.
