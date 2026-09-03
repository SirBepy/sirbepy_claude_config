# Shortcut quirks (Zirtue)

> Loaded by `SKILL.md` step 0 when `origin` is a `zirtue-corp` repo. Only what differs from the
> shared flow lives here.

Token extraction, dev UUID, mention name, git author, workflow-state IDs, and the `search/stories`
recipe: `~/.claude/refs/shortcut-api.md`. That file is canonical - fix drift there, not here.

## Why this platform needs a quirks file

Airion (PM) files epics, not tickets, so the dev files his own. Custom-field values are opaque
UUIDs nobody remembers, which is why they are pinned below rather than re-derived. The dev is solo
on the FE side of `zng-admin`, so branch-name generation is not part of this.

## API

REST is primary; the Shortcut MCP is frequently not connected. A single `POST /api/v3/stories`
accepts everything at once - name, description, type, owner, group, epic, workflow state, estimate
AND custom_fields - so no two-call split is needed.

```bash
TOKEN=$(grep -a SHORTCUT_API_TOKEN ~/.claude/.env | sed 's/^\xef\xbb\xbf//' | cut -d= -f2 | tr -d '\r\n')
curl -s -X POST "https://api.app.shortcut.com/api/v3/stories" \
  -H "Content-Type: application/json" -H "Shortcut-Token: $TOKEN" -d @payload.json
```

The `sed` strips a UTF-8 BOM. `~/.claude/.env` had one until 2026-08-18 and it silently broke the
Python reader in `hooks/shortcut-mutation-guard.py`; the bash path had worked around it here all
along.

## Pinned identity and defaults

These never change. Hardcode them, do not re-derive.

- Team / group_id: `ZNG ENG TEAM` (`6880fd7c-2327-429c-9483-f1490a6cfed3`)
- Workflow: `ENG - Core Workflow` (`500018252`). Default state To Do (`500018254`); use In Progress
  (`500018255`) or Testing (`500018257`) when the work is already done, and say so in the report.
- Workflow: `UI Design` (`500000012`) - some tickets (e.g. sc-54902) live here, not ENG. GET the
  story and check `workflow_id` before picking a state (SKILL.md Update step 2); ENG state ids
  4xx-error on a UI Design ticket. States (confirmed 2026-09-01): To Do (Backlog) `500000016`,
  Doing `500000013`, Ready for Review `500000033`, Done `500000017`, Done - Ready for Dev
  `500000034`, Won't Do `500004887`. No Testing equivalent - land on Ready for Review instead.
- Story type: `feature` for new functionality, `bug` for defects, `chore` for cleanup/analytics/
  config. Infer it, do not ask.
- 1 story point is roughly 4 hours.
- Iteration: **`54897` - ZNG Iteration Q3'26** (started, 2026-07-01 to 2026-09-30; verified
  2026-07-30). Default to it. Past 2026-09-30, call `GET /api/v3/iterations?status=started` once
  and update this line; fall back to none only if nothing is active.
- Stevan (BE) user id, for BE tickets filed on his behalf: `689917a7-ff0b-4b12-90dc-74bc55ce5915`

### Pinned custom fields (verified 2026-07-16)

Always send all five, as `{field_id, value_id}` pairs.

| Field | field_id | Values |
|---|---|---|
| Skill Set | `6216069e-0b41-45b7-8f1f-7d5e8b9b5983` | Frontend `6216069e-e3ed-403b-804c-f678c58b61a7`, Backend `6216069e-c745-4d0e-9722-39c6071c7e65` |
| Technical Area | `6216069e-ae53-4892-a4f2-d9cc796f1484` | Web App `6881029c-3921-4900-ad9a-197d3755d25f`, Admin Portal `6216069e-e33b-44b0-a3d8-15a130a5a88b` |
| ZNG: Product Area | `6881002d-700f-4bb7-b919-6cf8880ccdb9` | WebApp: Billers, RPPS, Billing Accounts `688101d5-cf51-4616-8aad-ed52a9b9a45b`, WebApp: Global `6881002d-2a43-40e9-964b-d72c3f556bcd`, AP: Billers `6977aec4-d5e1-4c55-a993-32a33bba368b` |
| Priority | `6260361c-cc5f-475f-9758-ea5b740e5b81` | High `6260361c-8f25-4cfd-941c-d32094abaca0`, Medium `6260361c-7ae3-4d8f-9594-fdff9c39fe4e` |
| Release | `68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb` | At creation only: **Next release** `698b4bce-ecd7-44c3-b62a-2b49b2506c1d` (the dev renumbers manually later). Never set on an existing ticket, including a state move - Joe sets it himself at actual release time |

**Repo to field mapping:**

| Repo | Skill Set | Technical Area | Product Area |
|---|---|---|---|
| zng-app | Frontend | Web App | per feature: `WebApp: Global`, `WebApp: Loan Creation`, `WebApp: Billers, RPPS, Billing Accounts` |
| zng-admin | Frontend | Admin Portal | usually `AP: Billers` |
| zng-biller | Frontend | Biller Portal | usually none |
| zng-api | Backend | Web App | `WebApp: Global` |

**Missing value_id?** Only the UUIDs above are pinned. When a needed value is not listed, `GET
/api/v3/custom-fields`, find it, use it, and append it to the table so it is pinned next time.
Never invent a UUID.

### Pinned epics (refresh when stale)

Current as of 2026-07-16. Offer the plausible ones as options; never ask open-ended.

- `53696` - ENG: ZNG - Biller Deeplink + Landing Page UI/UX
- `50688` - ENG: Bug pool:V2 (prod bugs with no feature epic)
- `53450` - ENG: Implement the AP: Biller Configuration Management
- `54104` - ENG: ZNG - Design & Implement Biller Portal (zng-biller)
- `54105` - ENG: ZNG - Non-RPPS Biller Payments & Remittance
- `53321` - ENG: Loan Creation Funnel Optimizations
- `54687` - ENG: Implement the AP: 'Partner' (not Biller) Configuration Management
- none - fine for standalone bugs and chores; the dev often files without an epic

Staleness check: if none fit, or the newest pinned epic is more than a quarter old, pull the epics
off the dev's 5 most recently updated stories and refresh this list.

## Create specifics

**Questions to front-load:** title (propose one plus an alternative), epic (2-3 plausible options
from the list, marked with a recommendation, never "name a reference ticket"), priority
(Low/Medium/High), estimate (1/2/3/5 points). Description defaults to "drafted from this
conversation" unless the dev has a spec to paste.

**Title style** - match the dev's existing tickets, never an invented convention:

- zng-app features/chores: `FE: <verb phrase>`
- zng-app bugs: `[FE] Area > Sub: symptom`
- zng-admin: `FE: AP: ...` - AP means Admin Portal, NEVER used for zng-app tickets
- zng-biller: `FE: BP: ...`
- zng-api, filed for Stevan: `BE: ...`

**The call:** one `POST /api/v3/stories` with `name`, `description`, `story_type`, `owner_ids`,
`group_id`, `epic_id` if chosen, `workflow_state_id`, `estimate`, and the full 5-field
`custom_fields` array. Capture the id and `app_url`.

**Relationships** are native story links, added after the create:

```bash
curl -s -X POST "https://api.app.shortcut.com/api/v3/story-links" \
  -H "Content-Type: application/json" -H "Shortcut-Token: $TOKEN" \
  -d '{"subject_id":<new_story_id>,"object_id":<related_story_id>,"verb":"relates to"}'
```

Verbs: `relates to` (default), `blocks`, `duplicates`. Link every BE/paired-FE counterpart.

## Update specifics - the destructive failure mode

**`PUT /stories/{id}` REPLACES the entire `custom_fields` array.** A partial PUT silently wipes
every field it did not mention. This is why the update path is GET, merge, then PUT, one story at a
time - never a bare PUT, and never skipping the GET because "nothing else should have changed".

```bash
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN" -o C:/tmp/sc_update_<id>.json
```

```python
existing = json.load(open(f'C:/tmp/sc_update_{sid}.json'))
merged = {cf['field_id']: cf for cf in existing.get('custom_fields', [])}
for change in requested_field_changes:      # [{field_id, value_id}, ...]
    merged[change['field_id']] = change
payload = {'custom_fields': list(merged.values())}   # plus name/description/workflow_state_id if changing
```

Include `name`, `description` and `workflow_state_id` only when they are actually changing. If no
custom field is changing, omit `custom_fields` from the payload entirely - that is the safest PUT,
and it is what a plain state move should send.

**Ownership:** `hooks/shortcut-mutation-guard.py` guards the MCP tools, not raw REST `curl` PUTs.
The REST path therefore carries no automatic owner check: use it for stories the dev named
explicitly, and never mutate one whose ownership he has not confirmed.

## Pickup specifics

Story ids are bare numbers; accept with or without an `sc-` prefix. With no id, search the dev's own
tickets (`query=owner:josipmui !is:archived`, `page_size=10`) via the recipe in
`refs/shortcut-api.md` and ask which one.

```bash
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN" -o C:/tmp/sc_<id>.json
```

Comment attachments (`![...](https://media.app.shortcut.com/...)`) are auth-gated - download with
the same `Shortcut-Token` header before reading:

```bash
curl -s "<attachment-url>" -H "Shortcut-Token: $TOKEN" -o C:/tmp/sc_<id>_<n>.png
```

Those `C:/tmp/` files are scratch, never referenced after the summary.

State move on go-ahead, from Backlog (`500018253`) or To Do (`500018254`) to In Progress
(`500018255`):

```bash
curl -s -X PUT "https://api.app.shortcut.com/api/v3/stories/<id>" \
  -H "Shortcut-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"workflow_state_id":500018255}'
```

Never include `custom_fields` in that PUT.

## Log

Append every create and every update to `~/.claude/skills/ticket/log.md` (gitignored). It is the
audit trail for the pinned defaults above: if a run contradicts a pinned value - a renamed epic, a
new field - fix the pinned section in the same session.

```
## sc-XXXXX - <title>
- Date: YYYY-MM-DD
- Action: create | update
- Epic / Iteration / Priority / Estimate: <values, creates only>
- Skill Set / Technical Area / Product Area / Release: <values, creates only>
- Fields changed, before -> after: <updates only>
- Workflow state: <state>
- Links: <relations or none>
- URL: https://app.shortcut.com/zirtue/story/XXXXX
- Notes: <ground-check verdict, anything unusual>
```
