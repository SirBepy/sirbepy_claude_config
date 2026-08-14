---
name: shortcut-create-ticket
description: Files a new Shortcut story for the dev using pinned defaults (no reference-ticket lookup), then logs the result.
disable-model-invocation: true
argument-hint: "[title/description] [priority] [estimate]"
---

# /shortcut-create-ticket

> File a new Shortcut story for the dev (`@josipmui`). All defaults are PINNED below — do not search other tickets to infer them. Log every ticket you create.

## Why this skill exists

- Airion (PM) files epics, not tickets. the dev has to file his own.
- Custom field values are opaque UUIDs, nobody remembers them — so they're pinned here.
- the dev is solo on the FE side of `zng-admin`, so branch name generation is NOT part of this skill.

## API access

REST is the primary path (the Shortcut MCP is frequently not connected). A single `POST /api/v3/stories` accepts everything: name, description, type, owner, group, epic, workflow state, estimate, AND custom_fields — no two-call split needed.

Token extraction: see `~/.claude/refs/shortcut-api.md`.

```bash
TOKEN=$(grep -a SHORTCUT_API_TOKEN ~/.claude/.env | sed 's/^\xef\xbb\xbf//' | cut -d= -f2 | tr -d '\r\n')
curl -s -X POST "https://api.app.shortcut.com/api/v3/stories" \
  -H "Content-Type: application/json" -H "Shortcut-Token: $TOKEN" -d @payload.json
```

If the MCP tools ARE connected, they work too (`stories-create` + `stories-update` split), but REST is fewer moving parts.

## Pinned identity & defaults

These never change. Hardcode them, don't re-derive:

Dev UUID, mention name, token extraction, and workflow-state IDs: see `~/.claude/refs/shortcut-api.md`.

- Team / group_id: `ZNG ENG TEAM` (`6880fd7c-2327-429c-9483-f1490a6cfed3`)
- Workflow: `ENG - Core Workflow` (`500018252`). Default state To Do (`500018254`); use In Progress (`500018255`)/Testing (`500018257`) when the work is already done (say so in the report).
- Story type: `feature` for new functionality, `bug` for defects, `chore` for cleanup/analytics/config. Infer from the work; don't ask.
- 1 story point ≈ 4 hours of work.
- Iteration: **`54897` — ZNG Iteration Q3'26** (started, 2026-07-01 → 2026-09-30; verified 2026-07-30). Default to it. Staleness check: past 2026-09-30, call `GET /api/v3/iterations?status=started` once and update this line — fall back to none only if nothing is active.
- Stevan (BE) user ID, for BE tickets filed on his behalf: `689917a7-ff0b-4b12-90dc-74bc55ce5915`

### Pinned custom fields (verified 2026-07-16)

Always send all five. `{field_id, value_id}` pairs:

| Field | field_id | Values |
|---|---|---|
| Skill Set | `6216069e-0b41-45b7-8f1f-7d5e8b9b5983` | Frontend `6216069e-e3ed-403b-804c-f678c58b61a7`, Backend `6216069e-c745-4d0e-9722-39c6071c7e65` |
| Technical Area | `6216069e-ae53-4892-a4f2-d9cc796f1484` | Web App `6881029c-3921-4900-ad9a-197d3755d25f`, Admin Portal `6216069e-e33b-44b0-a3d8-15a130a5a88b` |
| ZNG: Product Area | `6881002d-700f-4bb7-b919-6cf8880ccdb9` | WebApp: Billers, RPPS, Billing Accounts `688101d5-cf51-4616-8aad-ed52a9b9a45b`, WebApp: Global `6881002d-2a43-40e9-964b-d72c3f556bcd`, AP: Billers `6977aec4-d5e1-4c55-a993-32a33bba368b` |
| Priority | `6260361c-cc5f-475f-9758-ea5b740e5b81` | High `6260361c-8f25-4cfd-941c-d32094abaca0`, Medium `6260361c-7ae3-4d8f-9594-fdff9c39fe4e` |
| Release | `68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb` | ALWAYS **Next release** `698b4bce-ecd7-44c3-b62a-2b49b2506c1d` (the dev renumbers manually later) |

**Repo → field mapping:**

| Repo | Skill Set | Technical Area | Product Area |
|---|---|---|---|
| zng-app | Frontend | Web App | pick per feature: `WebApp: Global`, `WebApp: Loan Creation`, `WebApp: Billers, RPPS, Billing Accounts` |
| zng-admin | Frontend | Admin Portal | usually `AP: Billers` |
| zng-biller | Frontend | Biller Portal | usually none |
| zng-api | Backend | Web App | `WebApp: Global` |

**Missing value_id?** Only the UUIDs listed above are pinned. When a needed value (e.g. Technical Area "Admin Portal", Priority "Low") isn't listed: `GET /api/v3/custom-fields`, find it, use it, AND append it to the table above so it's pinned next time. Never invent a UUID.

### Pinned epics (refresh when stale)

Current ZNG-era epics (as of 2026-07-16) — offer the plausible ones as options, don't ask open-ended:

- `53696` — ENG: ZNG - Biller Deeplink + Landing Page UI/UX (biller flow, deeplinks, landing pages)
- `50688` — ENG: Bug pool:V2 (prod bugs with no feature epic)
- `53450` — ENG: Implement the AP: Biller Configuration Management (admin portal biller config)
- `54104` — ENG: ZNG - Design & Implement Biller Portal (zng-biller)
- `54105` — ENG: ZNG - Non-RPPS Biller Payments & Remittance
- `53321` — ENG: Loan Creation Funnel Optimizations
- `54687` — ENG: Implement the AP: 'Partner' (not Biller) Configuration Management (admin portal partner config)
- none — fine for standalone bugs/chores (the dev often files without an epic)

Staleness check: if none of these fit, or the newest pinned epic is >1 quarter old, pull the epics off the dev's 5 most recently updated stories (`search/stories?query=owner:josipmui !is:archived`) and refresh this list.

## Flow

### 0. FE "implement this design/flow" tickets - ground in current code first

Applies only to tickets that mean "implement X flow" or "build Y screen" against an existing FE app (zng-app/zng-admin/zng-biller); skip for bugs, chores, or BE tickets.

- Before drafting scope/description: read the current implementation of the affected screen/flow (dispatch an Explore subagent if it's a wide read) and diff it against the new design - never paraphrase a linked design ticket's spec text as if it were the diff.
- Confirm whether the visual reference is a live-product screenshot or a design-tool (Figma/Miro) mockup before picking a template - repro/actual/expected only fits a defect in a *running* product.
- Default to one ticket per shared root-cause/screen, not one per symptom found on it, unless the dev says otherwise.

Past incident (2026-07-21): a ticket was drafted by paraphrasing linked design-ticket spec text instead of reading `zng-admin`'s actual biller-group screens, and landed wrong until the dev pointed at the real code.

### 1. Front-load questions (AskUserQuestion, never open-ended)

Ask ONLY what can't be inferred, in one batch:

1. **Title** — propose one (see title style below) with an alternative; the dev picks or types his own.
2. **Epic** — offer 2-3 plausible options from the pinned list (mark a recommendation). Do NOT ask him to name a reference ticket.
3. **Priority** — Low / Medium / High. Recommend one based on the work.
4. **Estimate (1pt = 4h)** — 1 / 2 / 3 / 5, with a recommendation.

Description defaults to "drafted from this conversation" — don't ask unless the dev has a spec to paste. Skip any question the invocation already answered (e.g. `/shortcut-create-ticket high priority, 2 points`).

**State the claim.** Name the concrete file/behavior the ticket asserts is missing or broken, phrased as a literal string that will appear in a `grep` (a function, component, selector, or error text), not a paraphrase. That string is step 2's grep target.

**Title style** (match the dev's existing tickets, not invented conventions):
- zng-app features/chores: `FE: <verb phrase>` — e.g. `FE: Remove biller address dependency from loan creation`
- zng-app bugs: `[FE] Area > Sub: symptom` — e.g. `[FE] Login > Sign up: loan link redirect is lost after registration`
- zng-admin: `FE: AP: ...` — AP means Admin Portal; NEVER use it for zng-app tickets
- zng-biller: `FE: BP: ...`
- zng-api (filed for Stevan): `BE: ...`

### 2. Ground check (MANDATORY - never skip)

Run the three queries in `ground-check.md`: merged/open PRs, Shortcut with each hit's workflow state, and the stated claim at the tracked branch. A tracker search alone cannot see work that is already done.

- **Clean or soft signal:** write the `.shortcut-marker-<suffix>` file (`New-Item`, per `ground-check.md`) immediately before the create call, and note in the report what was checked and what could not be.
- **Hard stop** (Shortcut hit in Done/Testing, merged PR on the named file, or the symptom already absent at the tracked branch): do NOT write the marker. Report the hit (id, state, URL, or PR number and merge date) and stop. `shortcut-create-guard.py` blocks the create call without a marker, which is the mechanism working, not a failure.

### 3. Description — pick the smallest shape that fits

**Default: keep it short.** The dev consistently feels Claude-generated tickets are too long. When in doubt, write less.

#### Bug filed for a known engineer
Plain prose, ≤ 10 lines, no headings, no QA acceptance criteria:
- One short paragraph: what's happening, what's expected.
- A "Repro:" section: 3-5 numbered steps OR a tight bullet list.
- (Optional) one line of hypothesis.

#### Chore / small refactor / single tweak
1-3 sentences. What, why, where. No headings.

#### Feature for cold pickup (Airion-style)
Full three-section template ONLY when someone unrelated may pick it up cold weeks later:
1. **`# CONTEXT`** — plain English, no file paths. 2-5 sentences.
2. **`# ACTION ITEMS`** — the *what*, not the *how*. 3-6 bullets.
3. **`# ACCEPTANCE CRITERIA (QA)`** — numbered, scenario-grouped, runnable by a stranger. Include a **Regression** group.

Skip this template for anything smaller than a multi-day feature.

#### Relationships
No `# RELATED` text block — use native story links:

```bash
curl -s -X POST "https://api.app.shortcut.com/api/v3/story-links" \
  -H "Content-Type: application/json" -H "Shortcut-Token: $TOKEN" \
  -d '{"subject_id":<new_story_id>,"object_id":<related_story_id>,"verb":"relates to"}'
```

Verbs: `relates to` (default), `blocks`, `duplicates`. Link every BE/paired-FE counterpart.

**Sizing:** prefer smaller scopes AND smaller descriptions. Two independently shippable chunks = two tickets. If the dev is in a rush, one bigger ticket is fine.

### 4. Create — single REST POST

One `POST /api/v3/stories` with: `name`, `description`, `story_type`, `owner_ids`, `group_id`, `epic_id` (if chosen), `workflow_state_id`, `estimate`, and the full 5-field `custom_fields` array. Capture the returned story ID and `app_url`. Then add story links (step 3 shape) if any.

### 5. Log it

Append to `~/.claude/skills/shortcut-create-ticket/log.md`:

```
## sc-XXXXX — <title>
- Date: YYYY-MM-DD
- Team: <name>
- Epic: <id> <name> (or none)
- Iteration: <id or none>
- Priority: <value>
- Estimate: <points>
- Skill Set / Technical Area / Product Area / Release: <values>
- Workflow state: <state>
- Links: <relations or none>
- URL: https://app.shortcut.com/zirtue/story/XXXXX
- Notes: <dup-check keywords, anything unusual>
```

Why: the log is the audit trail for the pinned defaults. If a run contradicts a pinned value (renamed epic, new field), fix the pinned section in the same session.

### 6. Report

Tell the dev the new story ID + URL and which defaults were applied. If he also wants a draft comment on a related ticket, offer to draft it but do NOT post without approval.

## What this skill never does

- Never posts comments without explicit approval.
- Never updates existing tickets other than the one just created - for that, use `~/.claude/skills/shortcut-update-ticket/`.
- Never generates branch names. the dev handles Git.
- Never invents custom field UUIDs. Fetch unknown ones from `custom-fields-list` / `GET /api/v3/custom-fields` and pin them.
