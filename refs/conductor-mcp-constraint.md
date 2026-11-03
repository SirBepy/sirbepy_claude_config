# Conductor chats load only the generated MCP config: local servers never, claude.ai connectors when the project flag is on

Read this when an MCP tool you expect (Roblox Studio, figma, mobbin, a project's own `.mcp.json`
server, anything not prefixed `mcp__cc_conductor__` or `mcp__claude_ai_`) is missing from a Claude
Conductor-hosted chat's tool list. Restarting, respawning, or editing MCP config will not fix it for
a local server, because that tool was never reachable. A claude.ai account connector is the one
exception, covered below.

## The mechanism

Conductor spawns every chat with `--mcp-config <generated-path> --strict-mcp-config`
(`C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar\src-tauri\src\daemon\lifecycle\spawn.rs:178-182`,
re-read 2026-11-03). `--strict-mcp-config` makes that one generated file the **exclusive** MCP
source for the session. Ignored as a result: project `.mcp.json`, project `.claude/settings.json`
(`enabledMcpjsonServers`), and machine-local `C:\Users\tecno\.claude.json` (both its per-project
block and its top-level `mcpServers`). Local servers never load, and no restart, respawn,
approval, or config edit changes that.

**The one exception: claude.ai account connectors** (Google Drive, Claude Docs, Amplitude, ...).
Strict mode drops them too, so Conductor re-adds them itself: when the project's
`claude_ai_connectors` flag is on, it lists the account's connectors from the Anthropic API and
writes them into the generated file as `claudeai-proxy` entries
(`src-tauri\src\daemon\claude_ai_connectors.rs:1-9`; the call site is `spawn.rs:120-128`, which logs
`project flag on|off, N server(s)` per turn). The list is cached 10 minutes
(`claude_ai_connectors.rs:20-21`), so a connector Joe connects mid-session shows up on a later turn,
not instantly.

Receipt: 2026-10-27, zng-app hub chat "ZNG daily kickoff" (session 9dee5a6f). Joe connected
Amplitude, and `mcp__claude_ai_Amplitude__*`, `mcp__claude_ai_Google_Drive__*` and
`mcp__claude_ai_Claude_Docs__*` appeared mid-session and worked (`get_amplitude_context` returned the
ZIRTUE org and 5 projects).

Only the connectors are re-added, on purpose: an unauthenticated connector (mobbin, figma) once took
MCP init down and left the turn with no `approval_prompt` tool at all (`claude_usage_in_taskbar`
todo 867, DONE 2026-09-03, commit `1ac56b80`), which is why the strict flag exists and why the
re-add is flag-gated per project.

## When a claude.ai connector is missing

- Check the project's `claude_ai_connectors` flag in Conductor settings: off means none load.
- Check the connector is connected on the claude.ai account the chat runs under.
- Allow a turn or two: the list is cached for 10 minutes.
- Conductor's daemon log line `claude.ai connectors: project flag ... N server(s)` names which side
  came up empty.

## What works for a local server

- A Conductor change to merge extra servers into the generated per-session config (Joe's call,
  out of scope for a session to self-serve; must preserve todo 867's fix, so a broken third-party
  server can't take `approval_prompt` down again).
- Or: run Claude Code in a plain terminal, where no `--strict-mcp-config` is passed and a project
  `.mcp.json` loads normally (verified 2026-09-05: `claude mcp list` from a repo root showed the
  project's real MCP servers connected, outside Conductor).

## What does NOT work, ever, inside a Conductor chat

Restart, respawn, `/mcp` re-approval, editing `.mcp.json` or `.claude.json` - none of these can
surface a local (non-conductor, non-claude.ai) MCP tool in a Conductor-hosted session. Don't spend a
respawn cycle on it.
