<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=9, reconfirm-count=1, content-hash=6e0b4f2d -->
<!-- duplicate-checked -->
<!-- em-dash-exempt --> <!-- the Context block quotes the transcript string this guard must catch -->
# em-dash-guard's tool_result entries (type "user") shift the scan boundary past the tool_use it needs to catch

**Type:** skill-improvement
**Origin:** ai

## Goal

`hooks/em-dash-guard.py` (todo 307, extended by todo 350) misses an em dash inside a chat-tool
call's text arg (e.g. `send_message`) whenever ANY other tool call happens later in the same turn
(a follow-up `report_turn_status`, another tool, etc). Fix `iter_turn_tool_uses`'s turn-boundary
logic so it stops missing these.

## Context

Reproduced 2026-08-24 in zng-admin (session 7743f94c-4c39-4339-866d-a8e54d350f8a), transcript
`C:\Users\tecno\.claude\projects\C--Users-tecno-Desktop-Projects-zng-admin\7743f94c-4c39-4339-866d-a8e54d350f8a.jsonl`:

- Line 76: assistant calls `mcp__cc_conductor__send_message` with `text` containing a literal em
  dash ("...FE ticket — I've been implementing...").
- Line 77: the tool_result for that call arrives as a `{"type":"user", ...}` entry (tool_result
  blocks are wrapped in a `role: user` message in this transcript format - NOT a real human turn).
- Line 79: assistant calls `report_turn_status`.
- Line 80: that tool's tool_result, ALSO `{"type":"user", ...}`.
- Line 82: final assistant text "Draft sent above."
- Stop hook summary for this turn (transcript line 86, timestamp 15:43:37): `"Checking for em
  dash"` ran in 134ms with **no error** - it did not fire, despite the em dash being right there
  in line 76's `input.text`.

Root cause, read from `hooks/em-dash-guard.py:103-107` (`iter_turn_tool_uses`): it finds
`last_user_idx` as the index of the LAST entry anywhere in the transcript with `type == "user"`,
then only scans assistant tool_use blocks AFTER that index. But tool_result entries are also
`type: "user"` in this transcript format (confirmed: this session's transcript has 49 `"type":
"user"` entries against ~8 actual human prompts - the rest are tool_results). So the last
tool_result of the turn (line 80, `report_turn_status`'s result) becomes the boundary, and any
tool_use call BEFORE that boundary - including the exact `send_message` call the guard exists to
catch - is silently excluded from the scan. This isn't an edge case: it fires on essentially every
turn that makes 2+ tool calls after the real user prompt, which is the common case for
`send_message` immediately followed by `report_turn_status` (both required every turn per this
session's CLAUDE.md rules).

Todo 350 (done 2026-08-16) verified the allowlist and field-path mechanism with "22 test cases"
but evidently never covered a turn shape with a SECOND tool call after the chat-tool call - the
exact shape that's now the norm since `report_turn_status` became a mandatory every-turn call.

## Approach

1. Stop conflating "last real human turn" with "last type:user entry". Either:
   - Distinguish a genuine user prompt from a tool_result by content shape: a real prompt's
     `message.content` is a plain string (or a list without `tool_use_id`/`type: tool_result`
     entries); a tool_result's `message.content` is a list of dicts containing
     `type: tool_result`. Use that to find the true last-human-turn boundary instead of the last
     `type: user` entry.
   - Or, simpler and more robust: don't anchor on "after the last user turn" at all - scan ALL
     assistant tool_use blocks whose parent chain traces back to the current `promptId` (every
     entry in this transcript already carries a `promptId` field tying it to the originating human
     turn). Group by `promptId` and scan every tool_use under the CURRENT (last) `promptId`
     regardless of how many tool_results are interleaved.
2. Add a regression test case shaped exactly like this session's turn: chat-tool call (em dash) ->
   its tool_result -> a second, unrelated tool call -> its tool_result -> final text. Assert the
   guard still blocks.
3. Re-verify the existing 22 test cases still pass.

## Acceptance

- A `send_message`/`post_message`/`update_message` call containing U+2014, followed by ANY other
  tool call later in the same turn (especially `report_turn_status`), still gets blocked.
- Existing todo-350 test cases stay green.

## Notes

Filed from zng-admin (a project session) per CLAUDE.md's rule that global `~/.claude` findings go
in this repo's own backlog, never the surfacing project's. This session did not edit `~/.claude`
itself, only filed this todo. Concretely, this session drafted two Slack-message-for-teammate
messages with em dashes via `send_message` (turns at transcript lines 76 and 112) and BOTH shipped
unblocked; the dev caught it by eye and corrected Claude directly ("i HATE em dashes").
