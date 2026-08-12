<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Document REST fallback in shortcut-create-ticket skill instead of hard stop

**Type:** skill-improvement

## Goal

`~/.claude/skills/shortcut-create-ticket/SKILL.md` mandates `mcp__shortcut__*` tools and says to stop and tell the dev if `stories-update` is missing. Sessions frequently run without the Shortcut MCP connected; the REST API with `SHORTCUT_API_TOKEN` works fine and was used successfully (2026-07-16, sc-54786/54787). Update the skill to bless the REST path.

## Context

The 2026-07-16 zng-app session created two bug tickets purely via `POST /api/v3/stories` (single call carries custom_fields, estimate, workflow_state_id, group_id, owner_ids - no separate update call needed, unlike the MCP two-step). Token extraction and API quirks are already in project memories: reference-shortcut-api-token, reference-shortcut-put-replaces-custom-fields, reference-shortcut-workflow-states.

## Approach

Edit the skill's "Required tools" section: MCP tools preferred when connected; otherwise fall back to REST (`https://api.app.shortcut.com/api/v3`, header `Shortcut-Token` from `~/.claude/.env`, mind per-line BOM). Note that REST `POST /stories` accepts the full payload in one call, so steps 3-4 collapse. Keep the hard-stop only for the case where BOTH MCP and the token are unavailable.

## Acceptance

- Skill no longer instructs a dead-end stop when MCP is absent but the token exists.
- A cold session following the skill can file a fully-configured ticket via REST in one create call.

## Notes

- Dropped via /cleanup-todos 2026-08-11: already done - shortcut-create-ticket/SKILL.md:18-30 already blesses REST as primary. Confirmed by dev 2026-08-11.
