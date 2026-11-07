<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped write_draft / deferred tools 2026-10-27; only 1206 (done, different gap) and 1248 (Stop-hook idea) touch write_draft -->
# Claude calls deferred MCP tools without loading schemas, retries into duplicate drafts, and double-delivers text

**Type:** skill-improvement
**Origin:** dev
**Summary:** Conductor chats load tool schemas before the first call, do not blind-retry failed calls into extra side effects, and deliver text only once.

## Why

On 2026-10-27 a chat called deferred tools with guessed params, made four write_draft calls so Joe saw four draft windows, and pasted the same text twice.

## Goal

A Conductor chat stops flailing on `mcp__cc_conductor__*` tool calls: schemas are loaded before the first call, a failed call is not blind-retried into extra side effects, and one piece of text is delivered once.

## Context

Seen 2026-10-27 in a `claude_usage_in_taskbar` chat about a broken Clockify dashboard card. The Conductor tools (`send_message`, `write_draft`, `ask_user_question`, `spawn_chat`) are listed as DEFERRED, so only their names are known until `ToolSearch` loads the schema. The session called them straight away from guessed params:
- `send_message` with `message` (needs `text`): 1 failed call.
- `ask_user_question` with a flat `question`/`options` object (needs a `questions` array): 1 failed call.
- `write_draft` called 4 times: no `action`, then `action: create`, then `add` without `topic`, then `add` without a recipient. The tool's own error messages named each gap one at a time. Joe then saw 4 draft windows in the Drafts panel (screenshot in that chat).
- The same prompt text was then also pasted into a `send_message` blockquote, so Joe got it twice.
- `write_draft` is for a message addressed to a person or platform (it demands a recipient). A prompt meant for another Claude chat is not that, so the tool was the wrong choice from the start.
- After `spawn_chat` was denied by the permission check, the session moved on to other tools instead of stopping with one question to Joe.

UNVERIFIED: whether the 4 failed `write_draft` calls each left a draft window, or whether the windows came from something else; check the Drafts panel state or the daemon log for that session.

## Approach

Pick the cheapest mechanism that fits, in this order of preference:
1. A `PreToolUse` hook (or the existing tool-call guard) that blocks a call to a deferred `mcp__cc_conductor__*` tool when no `ToolSearch select:<tool>` for it appeared earlier in the session, with a message saying to load the schema first.
2. A short rule in `~/.claude/CLAUDE.md` Communication section: load deferred tool schemas in one `ToolSearch select:` call before first use; never retry a failing tool more than once without re-reading its error; `write_draft` is only for text addressed to a person or platform, a prompt for another chat goes inline or through `spawn_chat`; deliver text once, either as a draft or inline, never both.
Rejected: a blanket "never retry" rule, since a one-off param fix after reading the error is fine.

## Acceptance

- A blind first call to a deferred conductor tool is blocked or at least warned, naming `ToolSearch`.
- A test for the hook, if option 1 is taken, that fails without it.
- No regression: calls after a `ToolSearch select:` for that tool still pass untouched.

## Notes

- Related but different: 1248 (Stop-hook idea about turns that post a draft and end as done), 1206 (done, ticket comments routed via `write_draft`).
- Canary 2026-11-07: the harness does NOT reject a blind deferred-tool call (mcp browser_find called with an invented param and no ToolSearch reached the tool itself and returned its own error). So shipped option 1: hooks/deferred-tool-blind-call-guard.py denies the first call to any mcp__cc_conductor__ tool until the transcript shows a ToolSearch select: naming it or a tool_reference result for it (plain-text reminders ignored; per-session temp cache; fails open). The deny text also carries the write_draft / retry-once / deliver-once rules, so no CLAUDE.md line. Wired in settings.json; wiring proven by a nested claude -p run against a stub cc_conductor MCP: blind write_draft exit 2, ToolSearch then retry exit 0. Test hooks/test_deferred_tool_blind_call_guard.py. Unverified: whether the 4 draft windows came from the 4 failed calls.
