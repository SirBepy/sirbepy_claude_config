<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/955 wrote the ref; this corrects it -->
# 1254 - refs/conductor-mcp-constraint.md says no non-conductor MCP can load, but claude.ai connectors now do

**Type:** task
**Origin:** ai
**Created:** 2026-10-27
**Summary:** The Conductor MCP constraint doc and the global CLAUDE.md line match reality, so sessions stop saying an MCP can never appear in a Conductor chat.

## Why

On 2026-10-27 the Amplitude, Google Drive and Claude Docs connectors appeared mid-session in a Conductor chat and worked, contradicting the ref.

## Goal

Correct `~/.claude/refs/conductor-mcp-constraint.md` (and the global CLAUDE.md pointer to it) so sessions stop telling Joe an MCP can never appear in a Conductor chat.

## Context

The ref says `mcp__cc_conductor__*` is "the complete set of MCP tools that can exist" in a Conductor chat. On 2026-10-27, in the zng-app hub chat "ZNG daily kickoff" (session 9dee5a6f), Joe connected the Amplitude connector and `mcp__claude_ai_Amplitude__*`, `mcp__claude_ai_Google_Drive__*` and `mcp__claude_ai_Claude_Docs__*` appeared mid-session and worked (`get_amplitude_context` returned the ZIRTUE org and 5 projects). So claude.ai account connectors reach Conductor chats; only local `.mcp.json` / `.claude.json` servers may still be excluded (UNVERIFIED).

## Approach

1. Re-check `spawn.rs` in claude_usage_in_taskbar for how claude.ai connectors bypass `--strict-mcp-config`.
2. Rewrite the ref: which MCP sources load (claude.ai connectors: yes, mid-session) and which do not.
3. Update the global CLAUDE.md "A MISSING MCP tool" line to match.

## Acceptance

- The ref and CLAUDE.md line match observed behavior, with the receipt above.

## Notes

- Fixed in batch 2 (ref and respawn skill). CLAUDE.md line 22 still carries the stale sentence, left for pc-1281 (24 tokens of headroom).
