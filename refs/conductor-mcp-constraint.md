# Conductor sessions cannot load any non-conductor MCP server

Read this when an MCP tool you expect (Roblox Studio, figma, mobbin, a project's own `.mcp.json`
server, anything not prefixed `mcp__cc_conductor__`) is missing from a Claude Conductor-hosted
chat's tool list. Restarting, respawning, or editing MCP config will not fix it, because the tool
was never reachable in the first place.

## The mechanism

Conductor spawns every chat with `--mcp-config <generated-path> --strict-mcp-config`
(`C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar\src-tauri\src\daemon\lifecycle\spawn.rs:119,123`,
verified 2026-09-10). `--strict-mcp-config` makes that one generated file the **exclusive** MCP
source for the session. Ignored as a result: project `.mcp.json`, project `.claude/settings.json`
(`enabledMcpjsonServers`), and machine-local `C:\Users\tecno\.claude.json` (both its per-project
block and its top-level `mcpServers`).

The generated file holds exactly one server: `cc_conductor`. So in a Conductor chat,
`mcp__cc_conductor__*` is the complete set of MCP tools that can exist - no restart, respawn,
approval, or config edit changes that.

This is deliberate and recent, not a regression to revert: it fixes a real prior incident where an
unauthenticated account connector (mobbin, figma) took MCP init down and left the turn with no
`approval_prompt` tool at all (`claude_usage_in_taskbar` todo 867, DONE 2026-09-03, commit
`1ac56b80`).

## What actually works

- A Conductor change to merge extra servers into the generated per-session config (Joe's call,
  out of scope for a session to self-serve; must preserve todo 867's fix, so a broken third-party
  server can't take `approval_prompt` down again).
- Or: run Claude Code in a plain terminal, where no `--strict-mcp-config` is passed and a project
  `.mcp.json` loads normally (verified 2026-09-05: `claude mcp list` from a repo root showed the
  project's real MCP servers connected, outside Conductor).

## What does NOT work, ever, inside a Conductor chat

Restart, respawn, `/mcp` re-approval, editing `.mcp.json` or `.claude.json` - none of these can
surface a non-conductor MCP tool in a Conductor-hosted session. Don't spend a respawn cycle on it.
