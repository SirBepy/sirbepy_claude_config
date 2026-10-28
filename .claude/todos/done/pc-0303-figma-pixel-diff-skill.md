<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Consider a figma-pixel-diff skill

**Type:** skill-improvement

## Goal

This session repeated the same ad-hoc Figma verification workflow ~5 times (badge color,
TruStage icon, fee-summary chip bold/icon, "%" suffix alignment, logo-upload layout): fetch
a Figma node's rendered PNG + raw JSON via REST API, crop a region with PowerShell
`System.Drawing`, pixel-sample exact colors, cross-reference the JSON tree for exact copy
text/fills, then map sampled hexes to the nearest `CustomColors` token. Worth turning into a
proper skill rather than hand-rolling the same PowerShell/Python one-liners each time.

## Context

The mechanics now live in `~/.claude-personal/projects/.../memory/reference_figma_access.md`
(token location, API endpoints, crop/sample recipe) - that memory is the raw material for a
skill, not the skill itself. See `/bepy-skill-creator` for how to formalize this.

## Approach

Not to be drafted inline (per `/close`'s anti-pattern list - `/bepy-skill-creator` builds
skills, `/close` only surfaces the candidate). A future skill should probably:
- Accept a Figma URL (file key + node-id) and a personal access token (env var).
- Fetch + cache the node JSON and a rendered PNG in one step.
- Offer a "sample pixel at (x,y)" and "crop region" helper so repeated manual PowerShell
  scripting isn't needed every time.
- Optionally map a sampled hex to the nearest token in a project's `CustomColors`-equivalent
  file, flagging exact matches vs. "no existing token - possibly needs a new one" per this
  session's badge-color case.

## Acceptance

- Either a new skill exists covering this workflow, or this todo is explicitly declined
  (e.g. if the workflow doesn't recur enough to justify it) and closed.

## Notes

- Relocated from `32` in `zng-admin` via /cleanup-todos 2026-08-13: the artifact would be a new skill under `~/.claude/skills/`, a global-tree file, not a zng-admin one.
- Re-verified 2026-08-13: no `figma-pixel-diff` (or similarly named) skill exists under `C:\Users\tecno\.claude\skills`.
- Done 2026-08-13 as skills/figma-pixel-diff/, NOT declined. The todo permitted an explicit decline, but the spec turned out clearly buildable and not covered by 301's scripts. Built as a SEPARATE skill from figma-tiles rather than a mode of it: the two are different jobs (bulk board sweep versus single-node verification against an implementation), and merging them would force one 25-word description to cover two unrelated triggers. They share skills/_shared/figma_client.py so the quota handling cannot drift between them, mirroring the existing skills/_shared/playwright-resolve.cjs precedent. Subcommands: fetch (single node, inherently low quota by design), sample (pixel colour at x,y with optional radius averaging), crop, inspect (walks a cached tree for text and fills by name substring), and nearest-token (Euclidean RGB distance against a caller-supplied token map, reporting exact_match or needs_new_token). Verified offline against synthetic PNGs and JSON for both the exact-match and needs-new-token cases. UNTESTED: the network paths, no FIGMA_TOKEN available. Descriptions came in at 18 words each, well inside budget.
