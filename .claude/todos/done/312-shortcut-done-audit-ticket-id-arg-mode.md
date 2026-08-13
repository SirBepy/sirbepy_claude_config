<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Add a single-ticket-ID lookup mode to shortcut-done-audit

**Type:** skill-improvement
**Origin:** ai

## Goal

`/shortcut-done-audit` should support being invoked with a bare Shortcut story ID (e.g. `/shortcut-done-audit 54987`) as a fast-path, in addition to its existing state-scan mode.

## Context

`~/.claude/skills/shortcut-done-audit/SKILL.md`, "Args" section, only documents `states` (comma-separated workflow state names, default `Backlog,To Do,In Progress`). There is no documented path for "check this one specific ticket."

On 2026-07-31, the dev asked "is 54987 done, pushed, tested, should we mark it Testing?" â€” a single-ticket verification question, not a board scan. The skill was invoked anyway (`/shortcut-done-audit` with args `54987`), but its Flow (search API by owner+state, paginate, dedupe-cache gate, dispatch-volume gate) doesn't have a branch for "arg looks like a numeric ID, skip straight to a direct story fetch." Had to manually improvise: `GET /stories/{id}` directly, skip the search/dedupe-cache/dispatch-gate steps entirely, and `git log --grep` only the current repo (zng-biller) instead of the skill's fixed repo list, since the ticket was clearly biller-scoped from its title/description.

This worked fine ad hoc, but the skill gave no guidance for it â€” a cold session hitting the same request would have to reinvent the same detour.

## Approach

1. In the Args section, add: if the arg is purely numeric (or a list of numerics), treat it as explicit ticket ID(s) rather than state names. Skip step 2 (search API + pagination + target-state filter) entirely; fetch each ID directly via `GET /stories/{id}`.
2. Skip the dispatch-volume gate (step 5) for this mode too â€” the ticket count is already bounded by what the dev typed.
3. Still run step 3's commit/branch/PR matching and step 6's investigation questions, but scope the repo(s) searched to whichever repo(s) plausibly match the ticket (infer from title prefix, or just search all repos and let empty results fall out) instead of always searching every repo.
4. The dedupe cache (step 4) can still apply if useful, but for a single ad-hoc lookup it's fine to always do a fresh investigation rather than trusting a stale cache entry â€” note this as the default for ID-mode specifically.
5. Report format collapses to a single-ticket verdict (skip the "group by verdict" synthesis in step 7 when there's only one).

Rejected alternative: telling the dev to always use raw `curl` instead of the skill for single-ticket checks. Defeats the purpose of having a skill encode the investigation questions (returned? reproducible? scope match?) at all.

## Acceptance

- `/shortcut-done-audit 54987` (or any bare numeric ID) fetches that story directly, no search/pagination/dispatch-gate detour.
- Multiple space- or comma-separated IDs still work, one verdict per ticket, no forced "group by verdict" synthesis for a single ticket.
- Existing state-scan mode is unaffected.

## Notes

Relocated from 64 in zng-biller via /cleanup-todos 2026-08-13: targets the global ~/.claude/skills/shortcut-done-audit/SKILL.md, nothing zng-biller-specific in the fix itself.
- Done 2026-08-13, with one correction to the todo's own spec. Its Approach step 4 told the builder to reuse an existing dedupe cache in step 4 of the skill; no such cache exists, the real step 4 is the dispatch-volume gate. That reference was dropped rather than a cache being fabricated to match it. What shipped: the Args section documents ID mode (a numeric arg triggers a direct GET /stories/{id}, skipping search, pagination and state filtering), a new step 2b covers the direct-fetch flow and explicitly skips the dispatch-volume gate, step 3's repo scan is scoped to inferred repos in ID mode, and step 6 skips group-by-verdict for a single ticket.
