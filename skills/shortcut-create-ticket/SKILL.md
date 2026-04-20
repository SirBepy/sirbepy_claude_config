---
name: shortcut-create-ticket
description: Triggers on /shortcut-create-ticket only. Files a new Shortcut story for the dev, mirroring defaults from his existing assigned tickets, then logs the result.
---

# /shortcut-create-ticket

> File a new Shortcut story for the dev (`@josipmui`). Infer every default from tickets already assigned to him. Log every ticket you create so we can eventually pin real defaults.

## Why this skill exists

- Airion (PM) files epics, not tickets. the dev has to file his own.
- The Shortcut MCP splits creation across two calls: `stories-create` has no custom_fields/estimate/workflow_state params, `stories-update` is where those land. Skipping the update call leaves the ticket half-configured.
- Custom field values are opaque UUIDs, nobody remembers them.
- the dev is solo on the FE side of `zng-admin`, so branch name generation is NOT part of this skill.

## Required tools

- `mcp__shortcut__stories-search` (find the dev's reference tickets)
- `mcp__shortcut__stories-get-by-id` with `full: true` (read custom_fields from a reference)
- `mcp__shortcut__stories-create`
- `mcp__shortcut__stories-update` (custom fields, estimate, workflow state)
- `mcp__shortcut__iterations-get-active` (if no reference ticket supplies one)

If `stories-update` is missing/denied, stop and tell the dev to loosen `.claude/settings.local.json`.

## the dev's fixed identity

These never change. Hardcode them, don't re-derive:

- User ID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Mention name: `josipmui`
- Team: `ZNG ENG TEAM` (`6880fd7c-2327-429c-9483-f1490a6cfed3`)
- Default story type: `feature`
- Default workflow: `ENG - Core Workflow` (id `500018252`). Typical starting state: `To Do` (id `500018254`).
- 1 story point ≈ 4 hours of work. Estimate accordingly.

## Flow

### 1. Front-load questions (AskUserQuestion, never open-ended)

Ask the dev in one batch:

1. **Title** — open input. Hint the usual prefix `FE: AP: ...` unless he says otherwise.
2. **Description source** — options: "I'll paste it", "Draft from this conversation", "Mirror another ticket and tweak".
3. **Related ticket** (for epic/iteration inheritance) — options: a specific `sc-XXXXX`, "pick from my recent tickets", "none".
4. **Priority** — options: Low / Medium / High / Urgent.
5. **Estimate (story points, 1pt = 4h)** — options: 1 / 2 / 3 / 5 / 8 / "let me think".

Never ask mid-task. If the user's initial invocation already provided some of these (e.g. `/shortcut-create-ticket sc-53840 as reference, high priority, 3 points`), skip those questions.

### 2. Pick the reference ticket

- If the dev named one, use it.
- Otherwise call `stories-search` with `owner: "josipmui"` and `isArchived: false`. Take the 3-5 most recently updated. Show them with AskUserQuestion and let him pick.
- Read the reference with `stories-get-by-id` `full: true`. Pull: `team_id`, `epic_id`, `iteration_id`, `workflow_id`, each `custom_fields[].field_id`/`value_id`, the "Release" value.

### 2.5. Duplicate check (MANDATORY — never skip)

Before calling `stories-create`, search for an existing ticket that covers the same work. Someone else on the team may have already filed one.

- Call `stories-search` with the reference's `epic` (when set) plus `isArchived: false`, and skim the returned names for overlap with the proposed scope.
- Run a second `stories-search` with `name: "<distinctive keyword>"` and no epic filter, in case the existing ticket lives elsewhere. Pick a distinctive noun from the proposed work (e.g. `landing page URL`, `redirect route`) — not the boilerplate prefix.
- If a plausible match shows up, stop and ask with AskUserQuestion whether to (a) use the existing ticket, (b) file a new one anyway because the scope differs, or (c) cancel. Include the existing story ID + title so it's trivially judgeable.
- If nothing matches, proceed to step 3 and note in the reply that the check was performed ("No existing ticket found for X").

### 2.8. Description structure (Airion's standard, 2026-04-14)

Shortcut is the team's de-facto documentation. Non-engineers (PM, ops, UX) reference tickets too. Write descriptions so anyone on the team can pick them up cold.

**Structure:**

1. **`# CONTEXT`** — stupid simple. Plain-English explanation of what's changing and why, readable by someone who has never seen the code. No file paths, no function names, no jargon. 2-5 sentences is ideal. If you can't explain it without engineering terms, you don't understand the ticket yet.
2. **`# ACTION ITEMS`** — the **what**, not the **how**. Short bullet list naming what needs to exist when the ticket is done (a field, a screen, a route, a redirect behavior). No file paths, no function names, no implementation steps, no "call X then Y". 3-6 bullets. If a bullet starts explaining *how* to build it, delete that half. The engineer figures out the how at PR time.
3. **`# ACCEPTANCE CRITERIA (QA)`** — numbered, scenario-grouped, runnable by someone who has never seen the code. Group by flow/state ("Biller with custom URL configured", "Regression"), then list concrete click-through steps with expected outcomes. Avoid implementation language (no "calls X", "resolves Y"). Always include a **Regression** group listing what should keep working untouched.
4. **Relationships** — do NOT add a `# RELATED` text block. Use native Shortcut story links instead (they show up in the "Relationships" panel and stay in sync). The MCP doesn't expose link creation, so call the REST API directly:

    ```bash
    source ~/.claude/.env && curl -s -X POST "https://api.app.shortcut.com/api/v3/story-links" \
      -H "Content-Type: application/json" \
      -H "Shortcut-Token: $SHORTCUT_API_TOKEN" \
      -d '{"subject_id":<new_story_id>,"object_id":<related_story_id>,"verb":"relates to"}'
    ```

    Verbs: `relates to` (default), `blocks`, `duplicates`. Token lives in `~/.claude/.env` as `SHORTCUT_API_TOKEN`. Create a link for every BE/paired-FE ticket the new story depends on or pairs with.

**Sizing:**

- Prefer smaller tickets. If a ticket covers two independently shippable chunks (e.g. admin side + app side), split it.
- If the dev is in a rush, one bigger ticket is fine — trust his judgment.
- If the approach feels like it needs breakdown, break it down.

**Reason this exists:** Airion 2026-04-14 — "CONTEXT stupid simple, everything else as eng-oriented as you want. Referencing old SC tickets of past engineers has come in handy multiple times." Keep the signal high for both audiences.

### 3. Build the create payload

From the reference, inherit: `team`, `epic`, `iteration`, `owner` (always the dev, regardless of reference), `type: feature` (unless the dev said bug/chore).

Call `stories-create`. Capture the returned story ID.

### 4. Apply everything `stories-create` couldn't

Call `stories-update` with:

- `custom_fields`: array of `{field_id, value_id}` mirroring the reference, EXCEPT override the Priority value_id to match what the dev chose. Known field IDs (verify against `custom-fields-list` if unsure):
  - Skill Set: `6216069e-0b41-45b7-8f1f-7d5e8b9b5983` — Frontend: `6216069e-e3ed-403b-804c-f678c58b61a7`
  - Priority: `6260361c-cc5f-475f-9758-ea5b740e5b81` — values vary (High `6260361c-8f25-4cfd-941c-d32094abaca0`, others to be discovered via `custom-fields-list`)
  - ZNG: Product Area: `6881002d-700f-4bb7-b919-6cf8880ccdb9`
  - Technical Area: `6216069e-ae53-4892-a4f2-d9cc796f1484` — Web App: `6881029c-3921-4900-ad9a-197d3755d25f`
  - Release: `68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb` — ALWAYS set to **Next release** (`698b4bce-ecd7-44c3-b62a-2b49b2506c1d`) regardless of what the reference ticket had. the dev adjusts release numbers manually in the UI afterward.
- `estimate`: the point value the dev chose
- `workflow_state_id`: `500018254` ("To Do") unless the dev specifies otherwise

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

Why: after ~10 entries, the dev + I review the log and pin real hardcoded defaults so the reference-ticket step becomes optional.

### 6. Report

Tell the dev the new story ID + URL and which reference was used. If the dev also wants a draft comment to post on a related ticket (e.g. the "soft blocker" pattern), offer to draft it but do NOT post without approval.

## What this skill never does

- Never posts comments without explicit approval.
- Never updates existing tickets other than the one just created.
- Never generates branch names. the dev handles Git.
- Never invents custom field values. If a value isn't on the reference ticket, ask.
