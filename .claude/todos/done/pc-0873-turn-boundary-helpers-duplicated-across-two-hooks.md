<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The turn-boundary helpers are copy-pasted between em-dash-guard and ui-screenshot-reminder

**Type:** task
**Origin:** ai

## Goal

Move `is_tool_result_entry()` and `iter_turn_tool_uses()` into `hooks/_hooklib.py` so the two Stop
hooks that need them share one implementation instead of two byte-identical copies.

## Context

Found 2026-09-01 by `/code-check` over `0b471f0..HEAD`, Step 2 DRY pass, in an isolated review
subagent.

`hooks/ui-screenshot-reminder.py:83-123` carries `is_tool_result_entry()` and
`iter_turn_tool_uses()` copied from `hooks/em-dash-guard.py`, byte-identical except for one
docstring parenthetical. Neither goes through `_hooklib.py`, which has no such helper today.

The copy already carries a comment referencing todo 506 (the fix that taught this logic to anchor
the turn boundary on the last real human prompt rather than the last `tool_result`), so the mirror
is acknowledged in the source and was never extracted. That is the specific risk: the next fix to
turn-boundary detection lands in one copy and silently not the other, and the second hook keeps the
old bug with every test still green. 506 itself was a turn-boundary bug that went unnoticed for
weeks, which is what makes this worth more than a normal DRY nit.

## Approach

1. Read both copies and confirm they are still identical apart from the docstring; if they have
   already diverged, that divergence is itself the finding and needs resolving first.
2. Move the pair into `hooks/_hooklib.py` and import them in both hooks.
3. `hooks/_hooklib.py` is imported by 19 hooks and a break there kills every shell call in every
   session. `ci/run_all.py`'s hook-import smoke check (added by commit `e8010a0`) exec-loads all 19
   and must stay green.

## Acceptance

- `is_tool_result_entry` and `iter_turn_tool_uses` are defined exactly once in the repo.
- `hooks/test_em_dash_guard.py` and `hooks/test_ui_screenshot_reminder.py` both pass unmodified.
  Do not edit an existing assertion to fit the refactor; that is the one move that would hide a
  behaviour change here.
- `python ci/run_all.py` exits 0, hook-import smoke included.

## Notes

Pairs naturally with todo 874 (git-root resolution, the same shape in the same two files). Doing
them together is cheaper than twice, but they are independent and either can land alone.
- Completed in wave 2, commit 7142a64: is_tool_result_entry and iter_turn_tool_uses moved into hooks/_hooklib.py and both hooks import them. Each symbol now exists exactly once; both test suites pass unmodified.
