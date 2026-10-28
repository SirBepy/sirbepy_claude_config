<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=7, reconfirm-count=2, content-hash=1db481f0 -->
# No skill covers updating existing Shortcut stories, only creating new ones

**Type:** skill-improvement

## Goal

Give Shortcut story UPDATES (retitle, rescope description, move state, set custom fields) the same skill support that creation already has, so sessions stop hand-rolling one-off Python scripts against the REST API.

## Context

`~/.claude/skills/shortcut-create-ticket/` covers creating a story with pinned defaults. There is nothing for editing existing ones. `/shortcut-pickup-ticket` and `/do` read stories and move state, but neither exposes a general "update these fields on these stories" path.

On 2026-07-30 a single session hand-wrote four separate throwaway Python scripts to `C:/tmp/` to do: retitle two stories plus rewrite their descriptions, create five stories, move one story to Blocked, and append a blocker note to another. Every one of them re-implemented the same boilerplate:

- Reading `SHORTCUT_API_TOKEN` out of `~/.claude/.env` with BOM stripping (see the `reference_shortcut_api_token` memory, the BOM risk is per-line, not just line 1).
- The custom-field id table (Skill Set, Technical Area, ZNG Product Area, Priority, Release), which has to be re-fetched from `GET /custom-fields` or hardcoded fresh each time.
- Re-sending the full `custom_fields` array on every PUT, because a PUT replaces it wholesale (see the `reference_shortcut_put_replaces_custom_fields` memory). Forgetting this silently wipes a story's metadata.

That last one is the real hazard. It is a data-loss footgun that currently depends on the session remembering a memory file.

## Approach

Extend `~/.claude/skills/shortcut-create-ticket/` rather than adding a new skill, or add a sibling `shortcut-update-ticket`. Either way it needs:

1. A shared token-read helper with the BOM handling already solved, so it stops being re-derived.
2. The workflow-state id table (already captured in the `reference_shortcut_workflow_states` memory: Backlog 500018253, To Do 500018254, In Progress 500018255, PR Review 500018256, Testing 500018257, Blocked 500018415, Complete 500018258, Won't Do 500019415) and the custom-field id map, pinned in the skill instead of memory-only.
3. A safe PUT wrapper that GETs the story, merges the requested field changes into the existing `custom_fields`, then PUTs. Never a bare PUT with a partial array.
4. Support for acting on several story ids in one invocation, since the common shape is "retitle these two and move these three".

Must keep obeying the hard rule from the `feedback_never_comment_on_tickets` memory: state moves and field edits are fine, posting prose comments never is.

## Acceptance

- Retitling a story, rewriting its description, moving its state, and setting a custom field can all be done through the skill without writing a script.
- Custom fields survive an update that did not mention them.
- Running it against several stories in one go works.
- No path in it posts a comment to a story.

## Notes

- completed, commit fa3723a
