<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=EASY, worth=6, reconfirm-count=1, content-hash=7af3c2fd -->
# `figma-tiles` calls the desktop MCP server "unmetered"; Figma documents a daily cap

**Type:** skill-improvement
**Origin:** ai

## Goal

Correct the quota claim in `~/.claude/skills/figma-tiles/SKILL.md` so a future session doesn't
plan an unattended sweep around a limit that does not exist.

## Context

`skills/figma-tiles/SKILL.md:25-27` currently reads:

> **Unmetered alternative:** the Figma desktop app's Dev Mode MCP server (`127.0.0.1:3845`) has no
> quota, but it is selection-driven [...]

Figma's own docs give the desktop MCP server its own cap: **200 tool calls/day + 10-15/min** for a
Dev/Full seat on Starter/Pro, **600/day + 20/min** on Organization. `whoami`,
`add_code_connect_map` and `generate_figma_design` are exempt. Sources:

- https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/
- https://developers.figma.com/docs/figma-mcp-server/local-server-installation/

The "selection-driven" half of the sentence is accurate and independently confirmed, so only the
"has no quota" clause is wrong.

**Still unverified, do not assert either way:** whether the desktop MCP's daily budget shares a
bucket with the REST API quota. Figma's docs don't say. The auth paths differ entirely
(desktop-app session vs personal-access-token), so a separate bucket is likely, but that is an
inference. 200/day is in any case far more headroom than the REST `/nodes` endpoint, which died
after two calls on this Pro plan.

Also worth capturing while editing: Figma now documents a **remote** MCP server at
`https://mcp.figma.com/mcp`, available on all seats and plans, which the skill doesn't mention at
all. Whether it is node-id addressable (and therefore usable unattended, unlike the selection-driven
desktop one) was NOT established and needs its own check before the skill recommends it.

Found while researching how to read ~20-40 screens of a Figma file for zng-app's share-to-claim
work, 2026-08-19.

## Approach

1. Replace "has no quota" with the real numbers and cite the rate-limits doc.
2. Keep the "selection-driven, use it for a single screen, not this skill's job" guidance as is.
3. Optionally add a one-line pointer to the remote MCP server, explicitly marked as unverified for
   unattended/node-id use, so nobody plans a sweep around it either.

## Acceptance

- The skill no longer describes any Figma MCP surface as unmetered.
- The numbers carry their source URL.
- Nothing in the edit asserts the shared-vs-separate bucket question as settled.

## Notes

- bd54ba9: figma-tiles no longer claims the desktop MCP is unmetered; real published limits cited. Whether it shares a bucket with the REST quota was deliberately left unasserted.
