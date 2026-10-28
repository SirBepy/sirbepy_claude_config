<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=8, reconfirm-count=1, content-hash=f1dd6d49 -->
<!-- duplicate-checked 2026-09-05: grepped live backlog + done/ for "strict-mcp", "mcp-config", ".mcp.json". Live hits: only 950, which is about the restart GESTURE and whose open MCP-reload question this todo answers (950 updated in the same pass, they are complements not duplicates). done/ hit: 444, which is about skill/MCP scoping, unrelated. Nothing records the --strict-mcp-config fact itself. -->
# Nothing records that Conductor sessions cannot load any non-conductor MCP server

**Type:** rule-gap
**Origin:** ai

## Goal

Claude reasons about MCP using stock Claude Code's model: a project `.mcp.json` plus a trust
approval plus a session restart. In a Claude Conductor chat that model is simply wrong, and no
always-loaded surface says so. Record the fact once, so no future session rediscovers it.

Cost of not having it: **two `/respawn` cycles burned on 2026-09-05** in
`head_soccer_v_fable_oneshot`, chasing a Roblox Studio MCP server that could never have loaded.

## The fact (verified 2026-09-05, receipts below)

Conductor spawns every chat with `--strict-mcp-config` alongside `--mcp-config`, at
`C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar\src-tauri\src\daemon\lifecycle\spawn.rs:121`:

```rust
   .arg("--mcp-config")
   .arg(mcp_path)
   // todo 867: unmerged from account connectors, whose auth failures
   // took MCP init down and left the turn with no approval_prompt.
   .arg("--strict-mcp-config");
```

`--strict-mcp-config` makes that one generated file the **exclusive** MCP source. Ignored as a
result: project `.mcp.json`, project `.claude/settings.json` (`enabledMcpjsonServers`), and
machine-local `C:\Users\tecno\.claude.json` (both its per-project block and its top-level
`mcpServers`).

The generated file holds exactly one server. Verbatim from the session that found this:

```json
{"mcpServers":{"cc_conductor":{"args":["--mcp-permission"],"command":"C:\\Users\\tecno\\AppData\\Local\\Claude Conductor\\claude-conductor.exe","env":{"CC_SESSION_ID":"9e6b3ce4-74e6-4da9-b847-f7b24445658b"},"timeout":3660000}}}
```

**So in a Conductor chat, `mcp__cc_conductor__*` is the complete set of MCP tools that can exist.
No restart, respawn, approval, or config edit changes that.**

It is deliberate and recent, not a regression to revert:
`C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar\.claude\todos\done\867-second-concurrent-chat-can-spawn-without-the-cc-conductor-mcp-server.md`,
DONE 2026-09-03, commit `1ac56b80`. Unauthenticated account connectors (mobbin, figma) were taking
MCP init down and leaving turns with no `approval_prompt` tool at all.

### How it was confirmed, not inferred

- Live process: the session was PID 29164; its command line carried both `--mcp-config <path>` and
  `--strict-mcp-config`.
- The generated config at that path was read directly (quoted above).
- Independent cross-check: `ToolSearch` found no figma, playwright or mobbin tools either, and those
  are Joe's **user-scoped** servers with nothing to do with that repo. A session blind to its own
  user-level servers is not failing a per-project approval check.
- The Roblox server itself is healthy, so it is not a counter-example: its log
  (`...\Cache\C--Users-tecno-Desktop-Projects-head-soccer-v-fable-oneshot\mcp-logs-Roblox-Studio\2026-09-05T09-18-20-211Z.jsonl`)
  shows a clean stdio connect in 326ms, `serverVersion {"name":"RobloxStudio","version":"1.0.0"}`,
  `hasTools: true`. That was a `claude mcp` CLI probe, which does not pass `--strict-mcp-config`.

## Secondary: the advice at `skills/respawn/SKILL.md:16-19`

> If it isn't in your tool list, restart the app and retry first - MCP tools register at session
> start, so a session older than the tool won't see it yet.

Correct **for its own subject**, the `respawn` tool, which lives in the conductor config and so can
genuinely appear after a Conductor update. But it is the only written guidance on "an MCP tool is
missing", it generalizes badly, and it is the shape of reasoning that cost the two respawns above.
Worth a scoping clause rather than a rewrite.

## Approach

Preferred, cheapest, and it composes with 950 (which proposes a nearby bullet):

1. One bullet on an always-loaded surface (`~/.claude/CLAUDE.md`), stating the fact and the
   consequence: in Conductor, a missing non-conductor MCP tool is never fixable by restarting, so do
   not restart, do not respawn, and do not edit MCP config hoping to fix it.
2. A scoping clause at `skills/respawn/SKILL.md:16-19` so its restart advice reads as being about
   the `respawn` tool specifically.

Note the `~/.claude/CLAUDE.md` token ceiling in `ci/run_all.py` has zero headroom by design (see
`.claude/todos/PLAN.md`, Phase 0), so this may need a trade or a deliberate `CEILING_TOKENS` bump.
If neither is acceptable, the fallback is to put the fact in `~/.claude/refs/` and reference it from
the existing MCP-adjacent line rather than adding a new always-loaded bullet.

## What would actually make MCP work in Conductor (out of scope here, Joe's call)

- A Conductor change: merge extra servers into the generated per-session config. It owns the only
  MCP config a chat sees. Must preserve todo 867's fix, so a broken third-party server cannot take
  `approval_prompt` down again.
- Or: run Claude Code in a plain terminal, where no `--strict-mcp-config` is passed and a project
  `.mcp.json` loads normally. **VERIFIED 2026-09-05**: `claude mcp list` from that repo's root
  returned `Roblox_Studio: cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat - âś” Connected`, alongside
  `mobbin` and `plugin:figma:figma` both reporting `! Needs authentication` - which is itself a live
  corroboration of the exact failure Conductor's todo 867 was defending against.

## Acceptance

- The fact is recorded somewhere always-loaded, and `python ci/run_all.py` still passes.
- `skills/respawn/SKILL.md:16-19` no longer reads as general "missing MCP tool" advice.
- A cold session asked "why can't I see the Roblox MCP tools" answers from the ruleset alone,
  without re-reading Conductor's Rust source.

## Notes

Full investigation trail, including the falsified attempt-1 diagnosis (a "pending approval" in
`.claude.json`, which was the wrong file all along), is in
`C:\Users\tecno\Desktop\Projects\head_soccer_v_fable_oneshot\.for_bepy\mcp-respawn-log.md`.
That file is git-excluded and lives in a project repo, which is why the durable half is here.
- DONE 2026-09-10 via /loop-todos cycle 2. Recorded in all three places it needed to be. New refs/conductor-mcp-constraint.md holds the fact, the mechanism and the receipts. skills/respawn/SKILL.md:22-26 scopes its own restart advice: that advice is about the respawn tool specifically, because respawn lives in Conductor own generated per-session config and CAN genuinely appear after an update, and it explicitly does not generalise to any other missing MCP tool. The always-loaded half was added by the orchestrator rather than left to a follow-up, and folded into the existing restart bullet rather than added as a new one, which is what made it affordable: CLAUDE.md line 22 now carries the carve-out that a MISSING MCP tool is the exception no restart fixes, since Conductor spawns every chat with --strict-mcp-config so its generated config is the only MCP source that chat will ever see. Budget after: 6887 of 7000, headroom 113. The spawn.rs line numbers were re-verified rather than trusted: .arg("--mcp-config") at line 119 and .arg("--strict-mcp-config") at line 123, both inside the mcp_config_path block that opens at 116. python ci/run_all.py exits 0.
