<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Conductor's Stop hook blocks every turn when its own MCP server disconnects

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the Conductor Stop hook from creating an unsatisfiable turn-end loop when
the `cc_conductor` MCP server drops mid-session.

## Context

Reproduced on revaire-mobile, 2026-08-29, session
`455c73e7-93bc-4884-a870-be34eb9e1f1a`.

Mid-session the `cc_conductor` MCP server disconnected. A system-reminder listed
all 12 of its tools as no longer available and said *"Do not search for them,
ToolSearch will return no match"*.

The Stop hook then fired on every single turn end with:

> Before ending your turn, call BOTH tools: report_turn_status ... and
> send_message (the ONLY channel Joe sees ...)

Both tools belong to the disconnected server. The requirement was therefore
impossible to satisfy. It fired on roughly four consecutive turns. Confirmed
unavailable via three separate `ToolSearch` calls (two `select:` by exact name,
one keyword search), each returning "No matching deferred tools found".

Two knock-on problems, both worse than the noise:

1. The hook asserts `send_message` is *the only channel Joe sees*. If that were
   literally true, the model would have had no way to reach Joe at all for the
   rest of the session. In practice Joe kept replying to plain assistant text, so
   **the assertion in the hook text is wrong, or at least not universally true**,
   and it actively misleads the model into thinking it has gone silent.
2. The model burned turns re-checking for tools it had already been told were
   gone, because the hook kept insisting.

The server did reconnect on its own later, which is what ended it.

Hook command:
`curl -s --connect-timeout 2 --max-time 4 -X POST --data-binary @- -H 'Content-Type: application/json' http://127.0.0.1:27182/hooks/stop || exit 0`

## Approach

The fix belongs in the app (`claude_usage_in_taskbar`), which owns the hook
endpoint at `127.0.0.1:27182`.

1. **Make the requirement conditional on liveness.** The daemon knows whether the
   session's MCP transport is currently attached; it should not emit a blocking
   "call these tools" response when its own tools are unreachable. Degrade to a
   non-blocking response instead.
2. **Soften the wording.** "the ONLY channel Joe sees" should not be stated
   unconditionally, since it demonstrably was not true here. Something like
   "preferred channel; falls back to assistant text if the MCP is down".
3. **Consider auto-reconnect signalling** so the model is told when the tools
   come back, rather than discovering it from an ambiguous ambient reminder.

An Anthropic-facing `SendFeedback` draft was also queued during that session
describing the generic version of this (a Stop hook requiring MCP-provided
tools), but the concrete fix here is Joe's app.


## Notes

- Relocated to 824 in C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar via /cleanup-todos 2026-08-29: the Approach targets that app's own daemon Stop-hook code (it owns the 127.0.0.1:27182 endpoint), not any file in the global ~/.claude tree.