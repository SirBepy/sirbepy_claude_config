<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1108 is about chats self-closing when done, a different surface than chat titles -->
# Conductor chats are left without a title

**Type:** skill-improvement
**Origin:** dev
**Summary:** Every Conductor chat gets a short title early in the session so Joe can tell chats apart in the sidebar and recents.

## Why

On 2026-10-27 Joe pointed out Claude never gave a chat a title, so it showed its first-prompt text in recents.

## Goal

Every Conductor chat gets a short title early in the session, so Joe can tell chats apart in the sidebar and recents.

## Context

Seen 2026-10-27 in a `claude_usage_in_taskbar` chat ("why is the clockify thing not working?"): Joe pointed out Claude never gave the chat a title. The dashboard screenshot in that chat shows recently closed chats listed under their first-prompt text, which is what an untitled chat falls back to.

UNVERIFIED: which mechanism sets a title. Candidates to check: `~/.claude/skills/close/rename-session.ps1` (it has a `-GetId` mode and a `-Close` mode; read it to see whether it also renames), an MCP tool in the `cc_conductor` set, or an app-side auto-title. Read `rename-session.ps1` and the cc_conductor tool list (`ToolSearch`) before writing the fix.

## Approach

1. Find the supported way to set a chat title (see UNVERIFIED above).
2. Add a one-line rule to the global `CLAUDE.md` Communication section, or a skill, naming that mechanism: title the chat after the first real task, once, in the same step as the first reply.
3. If a hook can detect "no title yet after the first turn", prefer that over a prose rule.

## Acceptance

- A fresh chat is titled after its first task without Joe asking.
- The title is set once, not rewritten every turn.
