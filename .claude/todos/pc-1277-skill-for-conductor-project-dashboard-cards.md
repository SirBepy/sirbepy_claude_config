<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits are a deploy button (pc-0836) and commit step 7a (pc-1178), unrelated to dashboard cards -->
# Skill for adding and maintaining Conductor project dashboard cards

**Type:** skill-improvement
**Origin:** dev
**Summary:** A skill that puts a stat, list or HTML card on a Conductor project's dashboard the right way, so Joe can ask "show X on the dashboard" from any repo.

## Why

Joe, 2026-10-30, while designing `/global-claude-folder-audit`: he wanted a "days since the last audit" number on the `~/.claude` project dashboard, then said "honestly, we should make a skill for that lol... leave a todo to make a skill for it".

## Goal

A global skill (e.g. `/dashboard-card`) that takes "show <metric> on this project's dashboard" and ships a working card through the `mcp__cc_conductor__dashboard_card` tool: test first, then upsert, with an action button where one makes sense.

## Context

- The tool is `mcp__cc_conductor__dashboard_card` (deferred; load its schema with ToolSearch before calling). Actions: `list`, `test`, `upsert`, `delete`, `pin`. Sources are `{kind:http}` or `{kind:command}`. Displays are `stats`, `list` or `html`. The tool accepts these templates: `{{secret:NAME}}` (read from `~/.claude/.env`), `{{cwd}}`, `{{repo}}`, `{{today}}`, `{{week_start}}`, `{{now_iso}}`, `{{last_run:/cmd}}` (epoch ms of the latest chat run of a slash command). Command output can carry a top-level `_card` with `headline`, `headline_tone`, `progress` and `segments`. Source: the tool's own schema, read 2026-10-30.
- Gotchas from that schema: an HTML card renders in a sandboxed frame with no network, and inline `<script>` does not run in the installed app. Charts must use `_card.segments` / `_card.progress` instead. Secrets go through `env`, never `args`.
- First card built by hand: the `~/.claude` "days since /global-claude-folder-audit" card (2026-10-30). It runs a script that reads the skill's committed `ledger.md`. Use it as the reference example.
- A past session had a broken Clockify dashboard card in `claude_usage_in_taskbar` (mentioned in `pc-1252`). Read that chat with `/recall` for pitfalls before writing the skill.

## Approach

1. `/recall` the Clockify dashboard card chat and the 2026-10-30 audit-card chat for pitfalls.
2. Write the skill through `/bepy-skill-creator` conventions: when to use a command source vs http, the test-then-upsert loop, how secrets work, a `_card` headline/tone recipe, and a small helper-script pattern that emits JSON.
3. Include one worked example per display kind (stats, list, html).

## Acceptance

- From a fresh chat in some project, "put X on the dashboard" produces a card that renders real data on the first upsert, after a `test` call.
- The skill states the no-script/no-network HTML limit and the secrets-via-env rule.
