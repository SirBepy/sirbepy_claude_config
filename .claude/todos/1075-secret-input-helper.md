<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=HARD, worth=5, reconfirm-count=2, content-hash=46c68d56 -->
<!-- duplicate-checked: surfaced from mc_plugins_tag session 2026-10-03 -->
# A global way for Joe to hand Claude a secret without pasting it in chat

**Type:** skill-improvement
**Origin:** ai

## Goal
When Claude needs an API key or password, there is one standard, discoverable path that keeps the value out of the chat transcript.

## Context
2026-10-03, mc_plugins_tag: Joe needed to give Claude a Kinetic Panel API key and said "there should be an mcp function you can use so i can give u the key". No Conductor tool exists for secret input (checked the tool list). Claude wrote a project-local `server/set-secret.ps1`: a WinForms masked dialog that writes `key=value` to a gitignored properties file with BOM-less UTF-8 and only prints "saved N characters". Run with `powershell -NoProfile -STA -File ... -Key <k> -Label "<label>"`; it worked first try. Joe still felt an MCP tool should have existed.

## Approach
Either (a) promote the script to a global tool (e.g. `~/.claude/tools/set-secret.ps1` taking `-File <path> -Key <k>`) plus a short ref telling sessions to use it (announce the popup first per the popup-attribution rule), or (b) propose a Conductor MCP `request_secret` tool to the claude_usage_in_taskbar repo. (b) needs its own todo in that repo.

## Acceptance
- A session asked for a secret uses the standard helper without inventing one, and the value never appears in the transcript.

## Notes

- Phase 0 answer (Joe): route (b), file a Conductor MCP `request_secret` tool in claude_usage_in_taskbar's backlog; not the global set-secret.ps1. (2026-10-07, /loop-todos Phase 0)
