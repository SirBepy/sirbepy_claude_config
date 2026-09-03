<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 778 is about the exempt marker at commit time, 782 about message substance, 435 about the ruleset's breadth; none is about the check running after delivery -->
# em-dash-guard blocks the turn after the offending message has already reached Joe

**Type:** skill-improvement
**Origin:** ai

## Goal

Catch an em dash in a chat-tool call before the message is delivered, not after, so the rule
actually prevents Joe from seeing the character rather than only forcing the next message to be
clean.

## Context

Observed 2026-09-02 in a claude_usage_in_taskbar Conductor session
(`1bb05d7a-d7ae-40c0-8324-50981108f6e9`).

`mcp__cc_conductor__send_message` was called with an em dash in `text`. The tool returned
`{"message":1,"ok":true}` - the bubble was already rendered in Joe's chat. Only at turn end did
`hooks/em-dash-guard.py` fire and block with "rewrite using a comma, colon, or hyphen instead".
There is nothing left to rewrite at that point: the delivered message stands, and the block only
governs whatever is sent next.

The hook is wired as a `Stop` hook (`settings.json:449`), which is correct for
`last_assistant_message` - that text does not exist until the turn ends. But the MCP chat-tool
arm added later (the `CHAT_TOOL_TEXT_FIELDS` allowlist, per the module docstring's todo 350
lineage) scans tool calls that already ran, which is the half that is too late.

Not a duplicate of the neighbouring em-dash/send_message todos: 778 is about the exempt marker at
commit time, 782 is about a `send_message` that carries no substance, 435 is about the ruleset
being one hardcoded character. This one is purely about when the chat-tool half runs.

## Approach

Split the two arms rather than moving the whole hook:

1. Keep the `Stop` registration for `last_assistant_message` (it cannot move earlier).
2. Add a `PreToolUse` registration matching the same `CHAT_TOOL_TEXT_FIELDS` allowlist, returning
   a deny so the call never reaches the host. Reuse the existing module - gate the two arms on the
   payload's hook event name so there is one implementation and one character definition
   (`chr(0x2014)`, never a literal, per the module docstring).
3. Extend `hooks/test_em_dash_guard.py` with a PreToolUse-payload case for a flagged call and a
   clean one.
4. Consider mentioning `mcp__cc_conductor__update_message` in the deny text as the repair path for
   a message that slipped through by another route - it revises by ordinal, newest first.

## Acceptance

- A `send_message` call whose `text` contains U+2014 is denied at PreToolUse; the message never
  appears in the chat.
- The existing Stop-time check on `last_assistant_message` still blocks as before.
- `python ci/run_all.py` green (it runs `hooks/test_*.py`).
- A clean `send_message` is not blocked, and `Write`/`Edit`/`Bash` args stay unscanned, per todo
  307's scope decision.
