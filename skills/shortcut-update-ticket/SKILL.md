---
name: shortcut-update-ticket
description: Updates one or more existing Shortcut stories (retitle, rescope description, move workflow state, set a custom field) via a safe read-modify-write PUT that never wipes untouched custom_fields.
disable-model-invocation: true
argument-hint: "<ticket-id(s)> <field changes>"
---

# /shortcut-update-ticket

> Update existing Shortcut stories - retitle, rewrite description, move state, set a custom field - safely and in bulk. Companion to `/shortcut-create-ticket`, which only creates.

## Why this skill exists

On 2026-07-30 a session hand-wrote four throwaway Python scripts to `C:/tmp/` to retitle two stories, move one to Blocked, and append a blocker note to another - each re-deriving the token extraction, the workflow-state table, and (critically) the custom-field id map from scratch. The real hazard: `PUT /stories/{id}` REPLACES the entire `custom_fields` array. A partial PUT silently wipes every field it didn't mention. `zirtue-release-backfill`'s Apply step already proved the fix (GET, merge into the existing array, then PUT); this skill generalizes that pattern for ad hoc edits instead of one field.

## API access

REST is the primary path (Shortcut MCP is frequently not connected). Token extraction: `~/.claude/refs/shortcut-api.md`.

**Ownership note:** the `hooks/shortcut-mutation-guard.py` PreToolUse hook (wired in `settings.json`) only guards `mcp__shortcut__stories-update` and friends - it does not see raw REST `curl` PUTs. This skill is meant for stories the dev names explicitly (his own, or ones he's asked to be edited on someone's behalf); it does not re-implement the hook's owner check. Don't use it to mutate a story whose ownership hasn't been confirmed with the dev.

## Fixed identity & constants

Workflow-state IDs and dev UUID: `~/.claude/refs/shortcut-api.md`. Custom-field id map: the pinned table in `~/.claude/skills/shortcut-create-ticket/SKILL.md` ("Pinned custom fields") - reuse it, don't duplicate it here. If a needed value isn't listed, fetch it from `GET /api/v3/custom-fields` and pin it there (both skills read the same table).

## Flow

### 1. Resolve target story ids

Accept one or more ids (bare numbers or `sc-XXXXX`) and the field changes to apply. For "all stories matching X", search first, then confirm the resolved id list with the dev via AskUserQuestion before mutating anything - never act on an inferred set silently.

### 2. GET, merge, PUT - one story at a time, never a bare PUT

For each target id:

```bash
TOKEN=$(grep -a SHORTCUT_API_TOKEN ~/.claude/.env | sed 's/^\xef\xbb\xbf//' | cut -d= -f2 | tr -d '\r\n')
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN" -o C:/tmp/sc_update_<id>.json
```

Build the PUT payload from the cached JSON:
- `name` / `description` / `workflow_state_id`: include only the keys actually changing.
- `custom_fields`: if any custom field is changing, start from the existing array, key it by `field_id`, and overlay only the changed entries - every untouched field must survive in the payload. If no custom field is changing, omit `custom_fields` from the payload entirely.

```python
existing = json.load(open(f'C:/tmp/sc_update_{sid}.json'))
merged = {cf['field_id']: cf for cf in existing.get('custom_fields', [])}
for change in requested_field_changes:   # [{field_id, value_id}, ...]
    merged[change['field_id']] = change
payload = {'custom_fields': list(merged.values())}   # plus name/description/workflow_state_id if changing
```

```bash
curl -s -X PUT "https://api.app.shortcut.com/api/v3/stories/<id>" \
  -H "Content-Type: application/json" -H "Shortcut-Token: $TOKEN" -d @payload_<id>.json
```

**Never** send a `custom_fields` array that wasn't built from the freshly-GETed story. **Never** skip the GET because "nothing else should have changed."

### 3. Bulk targets

Repeat step 2 sequentially per id (not parallel - avoids rate-limit surprises). Report one result line per story: id, title, which fields changed, before → after for anything overwritten.

### 4. Log it

Append to `~/.claude/skills/shortcut-update-ticket/log.md`:

```
## sc-XXXXX - <title>
- Date: YYYY-MM-DD
- Fields changed: <name/description/state/custom field(s)>
- Before -> After: <short diff>
- URL: https://app.shortcut.com/zirtue/story/XXXXX
```

### 5. Report

Tell the dev which stories changed and what moved. If he also wants a comment posted, offer to draft it but do NOT post without approval.

## What this skill never does

- Never sends a partial `custom_fields` array - always GET, merge, then PUT.
- Never posts a comment.
- Never mutates a story without reading it first.
- Never invents a custom-field value_id - unknown ones get fetched and pinned in `shortcut-create-ticket/SKILL.md`'s shared table.
- Never mutates a story whose ownership the dev hasn't confirmed (see Ownership note above).
