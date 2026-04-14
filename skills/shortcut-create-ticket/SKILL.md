---
name: shortcut-create-ticket
description: Triggers on /shortcut-create-ticket only. Files a new Shortcut story for Joe, mirroring defaults from his existing assigned tickets, then logs the result.
---

# /shortcut-create-ticket

> File a new Shortcut story for Joe (`@josipmui`). Infer every default from tickets already assigned to him. Log every ticket you create so we can eventually pin real defaults.

## Why this skill exists

- Airion (PM) files epics, not tickets. Joe has to file his own.
- The Shortcut MCP splits creation across two calls: `stories-create` has no custom_fields/estimate/workflow_state params, `stories-update` is where those land. Skipping the update call leaves the ticket half-configured.
- Custom field values are opaque UUIDs, nobody remembers them.
- Joe is solo on the FE side of `zng-admin`, so branch name generation is NOT part of this skill.

## Required tools

- `mcp__shortcut__stories-search` (find Joe's reference tickets)
- `mcp__shortcut__stories-get-by-id` with `full: true` (read custom_fields from a reference)
- `mcp__shortcut__stories-create`
- `mcp__shortcut__stories-update` (custom fields, estimate, workflow state)
- `mcp__shortcut__iterations-get-active` (if no reference ticket supplies one)

If `stories-update` is missing/denied, stop and tell Joe to loosen `.claude/settings.local.json`.

## Joe's fixed identity

These never change. Hardcode them, don't re-derive:

- User ID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Mention name: `josipmui`
- Team: `ZNG ENG TEAM` (`6880fd7c-2327-429c-9483-f1490a6cfed3`)
- Default story type: `feature`
- Default workflow: `ENG - Core Workflow` (id `500018252`). Typical starting state: `To Do` (id `500018254`).
- 1 story point ≈ 4 hours of work. Estimate accordingly.

## Flow

### 1. Front-load questions (AskUserQuestion, never open-ended)

Ask Joe in one batch:

1. **Title** — open input. Hint the usual prefix `FE: AP: ...` unless he says otherwise.
2. **Description source** — options: "I'll paste it", "Draft from this conversation", "Mirror another ticket and tweak".
3. **Related ticket** (for epic/iteration inheritance) — options: a specific `sc-XXXXX`, "pick from my recent tickets", "none".
4. **Priority** — options: Low / Medium / High / Urgent.
5. **Estimate (story points, 1pt = 4h)** — options: 1 / 2 / 3 / 5 / 8 / "let me think".

Never ask mid-task. If the user's initial invocation already provided some of these (e.g. `/shortcut-create-ticket sc-53840 as reference, high priority, 3 points`), skip those questions.

### 2. Pick the reference ticket

- If Joe named one, use it.
- Otherwise call `stories-search` with `owner: "josipmui"` and `isArchived: false`. Take the 3-5 most recently updated. Show them with AskUserQuestion and let him pick.
- Read the reference with `stories-get-by-id` `full: true`. Pull: `team_id`, `epic_id`, `iteration_id`, `workflow_id`, each `custom_fields[].field_id`/`value_id`, the "Release" value.

### 2.5. Duplicate check (MANDATORY — never skip)

Before calling `stories-create`, search for an existing ticket that covers the same work. Someone else on the team may have already filed one.

- Call `stories-search` with the reference's `epic` (when set) plus `isArchived: false`, and skim the returned names for overlap with the proposed scope.
- Run a second `stories-search` with `name: "<distinctive keyword>"` and no epic filter, in case the existing ticket lives elsewhere. Pick a distinctive noun from the proposed work (e.g. `landing page URL`, `redirect route`) — not the boilerplate prefix.
- If a plausible match shows up, stop and ask with AskUserQuestion whether to (a) use the existing ticket, (b) file a new one anyway because the scope differs, or (c) cancel. Include the existing story ID + title so it's trivially judgeable.
- If nothing matches, proceed to step 3 and note in the reply that the check was performed ("No existing ticket found for X").

### 3. Build the create payload

From the reference, inherit: `team`, `epic`, `iteration`, `owner` (always Joe, regardless of reference), `type: feature` (unless Joe said bug/chore).

Call `stories-create`. Capture the returned story ID.

### 4. Apply everything `stories-create` couldn't

Call `stories-update` with:

- `custom_fields`: array of `{field_id, value_id}` mirroring the reference, EXCEPT override the Priority value_id to match what Joe chose. Known field IDs (verify against `custom-fields-list` if unsure):
  - Skill Set: `6216069e-0b41-45b7-8f1f-7d5e8b9b5983` — Frontend: `6216069e-e3ed-403b-804c-f678c58b61a7`
  - Priority: `6260361c-cc5f-475f-9758-ea5b740e5b81` — values vary (High `6260361c-8f25-4cfd-941c-d32094abaca0`, others to be discovered via `custom-fields-list`)
  - ZNG: Product Area: `6881002d-700f-4bb7-b919-6cf8880ccdb9`
  - Technical Area: `6216069e-ae53-4892-a4f2-d9cc796f1484` — Web App: `6881029c-3921-4900-ad9a-197d3755d25f`
  - Release: `68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb`
- `estimate`: the point value Joe chose
- `workflow_state_id`: `500018254` ("To Do") unless Joe specifies otherwise

If any custom field ID above looks stale, re-fetch with `custom-fields-list` before proceeding.

### 5. Log it

Append to `~/.claude/skills/shortcut-create-ticket/log.md` using this shape:

```
## sc-XXXXX — <title>
- Date: YYYY-MM-DD
- Reference ticket: sc-YYYYY
- Team: <name>
- Epic: <id> <name>
- Iteration: <id> <name>
- Priority: <value>
- Estimate: <points>
- Skill Set / Technical Area / Product Area / Release: <values>
- URL: https://app.shortcut.com/zirtue/story/XXXXX
```

Why: after ~10 entries, Joe + I review the log and pin real hardcoded defaults so the reference-ticket step becomes optional.

### 6. Report

Tell Joe the new story ID + URL and which reference was used. If Joe also wants a draft comment to post on a related ticket (e.g. the "soft blocker" pattern), offer to draft it but do NOT post without approval.

## What this skill never does

- Never posts comments without explicit approval.
- Never updates existing tickets other than the one just created.
- Never generates branch names. Joe handles Git.
- Never invents custom field values. If a value isn't on the reference ticket, ask.
