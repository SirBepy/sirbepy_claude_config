<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Em-dash Stop hook only scans last_assistant_message, misses MCP tool call text args

**Type:** skill-improvement
**Origin:** ai

## Goal

`hooks/em-dash-guard.py` (todo 307, done 2026-08-13) blocks an em dash in Claude's final prose
response, but an em dash embedded inside an MCP tool call's own text argument (e.g.
`mcp__cc_conductor__post_message`'s `text` param, `send_message`'s `text` param, an
`ask_user_question` option `description`) ships unblocked, since those are tool_use content
blocks, not the `last_assistant_message` the Stop hook inspects.

## Context

Reproduced 2026-08-16 in claude_usage_in_taskbar (session d69de267): a `post_message` call to the
repo-coordination channel read "...won't rebuild/restart the live app without asking first" with
a literal em dash before "won't". The message posted successfully; no Stop-hook block fired,
because Stop hooks only see the turn's own composed prose, not the arguments of tool calls made
during the turn (see 307's Notes: "last_assistant_message only ever carries Claude's own composed
text: tool_use and tool_result are separate content blocks" - that was framed as the reason no
extra scoping was needed for false positives, but it's also the reason true positives inside
tool_use args go unseen).

`post_message`/`send_message` content is genuinely Claude-authored prose (not a quoted file, not
tool output) and per `feedback_em_dash_scope.md` ("code+messages only") is exactly the kind of
content the rule is meant to cover - a peer-channel or user-facing chat bubble reads the same as
assistant prose to the human/session on the other end.

## Approach

1. Read `hooks/em-dash-guard.py` and the Stop hook payload shape to confirm what's actually
   available (transcript path, most likely) - the Stop hook may already have access to the full
   turn's tool_use blocks via the transcript file, not just `last_assistant_message`.
2. Extend the scan to the `text` (or equivalent) argument of tool_use blocks for a documented
   allowlist of "chat content" tools - at minimum `mcp__cc_conductor__post_message`,
   `mcp__cc_conductor__send_message`, `mcp__cc_conductor__ask_user_question` (question/option
   description fields). Do not scan every tool's every argument (e.g. `Write`/`Edit` file content
   or `Bash` commands legitimately quote external text) - scope to the same "Claude-authored chat
   prose" surface the original todo targeted, not tool inputs in general.
3. Same block-and-rewrite mechanism as the existing hook: block with the offending snippet so the
   tool call gets redone with the em dash fixed before it actually reaches the peer/user.

Rejected alternative: widening the em-dash guard to scan everything in every tool_use block -
too broad, would false-positive on legitimately-quoted external text (file content, command
output, pasted user text containing an em dash).

## Acceptance

- A `post_message`/`send_message` call whose text contains U+2014 gets blocked before it reaches
  the recipient, same as a violation in final prose does today.
- A `Write`/`Edit`/`Bash` call containing an em dash inside file content or a command string is
  NOT blocked (matches the existing scope decision in 307).
- Verify by deliberately calling `post_message` with an em dash in a test session and confirming
  the block fires.

## Notes

Filed from claude_usage_in_taskbar (a project session) per CLAUDE.md's rule that global `~/.claude`
findings go in this repo's own backlog, never the surfacing project's. This session did not edit
`~/.claude` itself, only filed this todo.
- Done 2026-08-16, commit 005490c. em-dash-guard.py now also scans the text args of an allowlisted set of chat tools (send_message, post_message, update_message, ask_user_question, matched by name suffix so a differently-prefixed MCP server is still caught), read from transcript_path. Write/Edit/Bash stay unscanned per todo 307's scope decision. 22 test cases pass, all 9 hook suites green. The retry-loop risk is covered by the pre-existing stop_hook_active guard at line 132, verified by reading it.
