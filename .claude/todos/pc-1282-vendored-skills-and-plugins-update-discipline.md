<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: audit bundle 6; pc-1191 tracks only the impeccable CI symptom -->
# Vendored skills and plugins: re-apply local overrides after updates, decide Cloudflare deletes, Figma plugin, synced bundle

**Type:** task
**Origin:** dev
**Summary:** Vendor updates stop silently undoing local tweaks, and unused vendored skills and plugin skills stop crowding every session.

## Why

Joe accepted this bundle from the 2026-10-30 `/global-claude-folder-audit` run, and chose "disable the Figma plugin globally" with the note: "I know we do actually use the Figma MCP but at that point do we even need these Figma skills? Probably not, right?" A 3-agent panel then found facts that change that call (below), so nothing was disabled or deleted that night.

## Goal

Every vendored tree has a recorded source and a way to re-apply local overrides, and the skill listing carries only plugins the dev uses.

## Context

- impeccable: an uncommitted 4.5.0 -> 4.5.2 re-vendor (13 files plus `agents/impeccable-asset-producer.md`, dirty since 2026-10-13, another session's work) replaced the trimmed description at `skills/impeccable/SKILL.md:3` with 118 words, so local `ci/run_all.py` fails the description budget. Upstream's `npx impeccable update` overwrites in place; `~/.impeccable/update-check.json` already announces 4.8.0; `skills/VENDORED.md` still says 4.5.0. pc-1191 notes the symptom.
- Cloudflare pack: frozen copy of github.com/cloudflare/skills @ 4cc2977 (2026-08-12), no SOURCE note, only `wrangler` locally modified. Refuted delete set: `cloudflare-one`, `cloudflare-one-migrations`, `sandbox-sdk` (umbrella `cloudflare/references/sandbox` is a superset), `agents-sdk` (weakest: the umbrella does NOT contain its 19 refs), `turnstile-spin`, `web-perf` (needs a chrome-devtools MCP that is not configured). All are slash-only, so deleting saves no listing tokens, only tidiness; the devil's-advocate panelist argued to leave them. Keep `cloudflare`, `wrangler`, `durable-objects`, `workers-best-practices`, `cloudflare-email-service` (hubbub is a Worker with Durable Objects and KV).
- Figma: the plugin `figma@claude-plugins-official` 2.2.157 (`settings.json` enabledPlugins ~747) ships BOTH 16 skills (~1,022 listing words per session, zero use in transcripts) AND the remote Figma MCP (`.mcp.json` -> https://mcp.figma.com/mcp). Disabling it removes that MCP everywhere except zng-admin, which has a project-scoped `figma` server in `.claude-personal/.claude.json`. Separately, the allow rule `mcp__figma__get_figma_data` matches a user-level stdio server (figma-developer-mcp, API key) in `~/.claude.json` that survives a plugin disable. Enabled deliberately in 882d611 (2026-08-19). `/figma-tiles` and `/figma-pixel-diff` use the REST token via `skills/_shared/figma_client.py`, not any MCP, and do things the MCP does not: whole-board sweeps to PNG tiles with manifest and comment digest, disk cache with 429/Retry-After backoff (pc-0386: MCP is metered, 100-hour Retry-After incidents), offline export slicing, Dev Mode annotation digest, nearest-token matching, local two-screenshot diff. So they are not redundant.
- Synced Claude-app bundle (`skills/synced/`, gitignored): ~14 `anthropic-skills:*` entries per session, including a stale model-invocable `bepy-skill-creator` copy that contradicts the local one and `anthropic-skills:todo` (writes TODOs.md and auto-commits, against the `.claude/todos` contract). `skillOverrides` has 11 bare keys; whether it accepts namespaced `plugin:skill` keys is UNVERIFIED.

## Approach

1. Ask the dev which Figma MCP he actually uses (remote OAuth one from the plugin, or the API-key stdio one). If the remote one: keep the plugin and try hiding its 16 skills via `skillOverrides` (test one namespaced key first). If not: disable the plugin and keep `/figma-tiles` and `/figma-pixel-diff`.
2. Add `skills/VENDORED.overrides.json` (local tweaks per vendored file: impeccable description, Cloudflare `disable-model-invocation` flags, asd-ste100) plus a re-apply script, run after any vendor update and checked in CI; add a SOURCE/commit line per pack in `skills/VENDORED.md`.
3. Coordinate with whoever owns the dirty impeccable tree (or ask the dev) before committing it with the trimmed description restored.
4. Ask the dev about the 6 Cloudflare deletes; if yes, delete with their `VENDORED.md` rows (30,33,34,36,37,38 and prose at 65-69).
5. Turn off `anthropic-skills:todo` and the synced `bepy-skill-creator` via `skillOverrides` if namespaced keys work.

## Acceptance

- Figma: settled, see Notes; no Figma change is part of this todo any more.
- A simulated vendor update followed by the re-apply step leaves `ci/run_all.py` green.
- Session skill listing drops the hidden/removed entries (check a fresh session's listing).

## Notes

- 2026-10-30, Joe: he uses the remote Figma MCP (the plugin's mcp.figma.com one) and "i wanna be able to use figma still, cuz i do, but its true that ive never once invoked ANY figma skill".
- 2026-10-30, tested: `skillOverrides` "name-only" has NO effect on plugin skills, with either `figma:figma-use` or bare `figma-use` keys (nested `claude -p` listing check after each edit; both reverted). So the only way to drop the 16 skills is to disable the plugin and re-add the remote MCP directly, e.g. `claude mcp add --transport http figma https://mcp.figma.com/mcp --scope user` (exact flag order UNVERIFIED, check `claude mcp add --help`), then re-authenticate once via `/mcp`. Note six plugin skills (`figma-use`, `figma-design-to-code`, `figma-generate-design`, `figma-generate-diagram`, `figma-generative-plugins`, `figma-shaders`) describe themselves as mandatory prerequisites for MCP tool calls, yet zero were invoked in 9 weeks of transcripts while the MCP was used. Waiting on the dev's choice.
- 2026-10-30, Joe: "i just wants most efficient... i just want claude to still be able to do equally as good work". A transcript scan (all raw transcripts under `~/.claude/projects`, 2026-08-26..10-30) found zero Figma MCP tool calls of any kind (`mcp__plugin_figma*`, `mcp__figma__*`, `mcp__claude_ai_Figma*`). So the plugin is now disabled at user scope (`settings.json` enabledPlugins `figma@claude-plugins-official: false`). For a repo that does Figma design-to-code work, enable it per project instead (`enabledPlugins` in that repo's `.claude/settings.local.json`, or `/plugin` at project scope), which brings back both the remote MCP and its prerequisite skills there only. zng-admin keeps its own project-scoped `figma` MCP server in `.claude-personal/.claude.json` regardless. Figma part of this todo: done.
