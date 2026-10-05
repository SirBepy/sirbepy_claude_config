<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1032 (done) was the relay exemption, 410 (done) the relay-only silent turn, 332/491 the flagged-skill hook; this is the counter's turn-window scoping, a different defect -->
# send-message stop guard misses a send_message made before a mid-turn injected message

**Type:** task
**Origin:** ai

## Goal

`hooks/send-message-stop-guard.py` resets its silent-turn counter whenever a turn did call
`send_message`, including turns where a background-agent hand-back or task notification was
injected partway through.

## Context

Observed 2026-10-05 in the /loop-todos session 6a91: the guard blocked with "3, 4, 5 consecutive
turns ... no send_message" across turns that each DID call `mcp__cc_conductor__send_message`.
Those turns had a subagent hand-back or task-notification delivered as a user-type transcript entry
while the turn's own tool calls were still running.

UNVERIFIED: the guard's `_turn_tool_suffixes(transcript_path)` (hooks/send-message-stop-guard.py:100)
scopes "this turn" from the last user-type entry, so an injected entry after the `send_message` call
truncates the window and hides it. Would check by reading `_turn_tool_suffixes` and replaying a
transcript slice with an injected entry between `send_message` and `report_turn_status`.

Not caused by todo 1032's change (181d1a2 only added `post_message` to RELAY_SAFE_SUFFIXES).

## Approach

1. Confirm the turn-boundary hypothesis against a real transcript slice.
2. If confirmed: anchor the turn start on the last REAL user prompt (the same test
   `_last_real_user_text` already uses), skipping injected agent hand-backs, task notifications and
   stop-hook feedback.
3. Regression case in `hooks/test_send_message_stop_guard.py`: send_message, then an injected
   hand-back entry, then report_turn_status, must reset the counter.

## Acceptance

- The regression case is RED against the current hook and GREEN after.
- A turn with no send_message at all still increments, unchanged.
