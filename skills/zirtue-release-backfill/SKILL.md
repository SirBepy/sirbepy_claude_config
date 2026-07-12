---
name: zirtue-release-backfill
description: Triggers on /zirtue-release-backfill only. Backfills the Shortcut Release field (and other missing scope metadata) on tickets the dev shipped code for, by matching merge SHAs against git tags. Always reports first, applies only after explicit approval.
---

# /zirtue-release-backfill

> Backfill the Shortcut **Release** custom field (and any other missing scope metadata) on every ticket the dev shipped code for. Always report first, apply only after explicit approval.

## Why this skill exists

- Tickets often sit in `Ready for deploy` (or get pushed to `Complete`) without a concrete Release value set. PM wants it populated so deploy notes / release summaries are accurate.
- The dev frequently inherits or hands off tickets, so "currently owned by me" misses real work. Source of truth for "I shipped this" is the git author log.
- The mapping is mechanical but spread across three repos and Shortcut's enum values. Easy to get wrong by hand.
- Running it as a skill keeps the procedure consistent every time the dev wants to do a pass.

## Args

```
/zirtue-release-backfill [state]
```

- `state` (optional) — Shortcut workflow state name to filter on. Default: `Ready for deploy`. Examples: `Complete`, `Testing`, `PR Review`, `In Development`.
- If the dev passes an unknown state, ask with AskUserQuestion listing the actual state names from the `ENG - Core Workflow` (workflow id `500018252`).

## Required tools

- `Bash` — git tag / log / fetch in the three repos; curl against Shortcut REST API.
- `Agent` (`general-purpose`) — only if the candidate set is large (>20) and parallelism actually helps. For typical batches (≤20), inline mechanical lookup is faster.

**Shortcut API access:** the Shortcut MCP server is often unavailable. Always have the REST fallback ready (token in `~/.claude/.env`, header `Shortcut-Token`).

## Fixed identity & constants

Never re-derive:

- Dev Shortcut UUID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Dev mention name: `josipmui`
- Dev git author: `JosipMuzicZirtue` (email `josip.muzic+zirtue@cinnamon.agency`)
- Release custom field UUID: `68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb`
- Other custom field UUIDs:
  - Priority: `6260361c-cc5f-475f-9758-ea5b740e5b81`
  - Skill Set: `6216069e-0b41-45b7-8f1f-7d5e8b9b5983`
  - ZNG: Product Area: `6881002d-700f-4bb7-b919-6cf8880ccdb9`
  - Technical Area: `6216069e-ae53-4892-a4f2-d9cc796f1484`
- Workflow state IDs (ENG - Core Workflow `500018252`):
  - `Ready for deploy`: `500018659`
  - `Complete`: `500018258`
- Sentinel Release values (treat as unset):
  - `Next release` — value_id `698b4bce-ecd7-44c3-b62a-2b49b2506c1d`
  - `TBD` — value_id `698b510b-c54a-4adb-b47f-93a06852afe1`
  - `Oneday` — value_id `69247286-4a0c-4fcf-a3c4-85f8bf6af1ea`
  - `V1.0`, `V1.1`, `V2.0` — legacy placeholders
- Repos (sibling paths):
  - `C:/Users/tecno/Desktop/Projects/zng-app` — Flutter web consumer app. Tag format: `v1.0.0+N` (build) + `Release-MM-DD-YYYY` (deploy). Shortcut label: `FE 1.0.0+N`.
  - `C:/Users/tecno/Desktop/Projects/zng-admin` — Flutter web admin. Tags `v1.0.0+N` + `Release-MM-DD-YYYY`. Shortcut label: `Admin 1.0.0+N`.
  - `C:/Users/tecno/Desktop/Projects/zng-api` — NestJS backend. Tags `v1.0.X`. Shortcut label: `API 1.0.X`. (Read-only here; dev does not author API commits.)

## CRITICAL: Shortcut PUT semantics

**`PUT /stories/{id}` with a `custom_fields` array REPLACES the entire array — it does NOT merge.** Sending `{"custom_fields":[{Release only}]}` will wipe Skill Set, Product Area, Priority, etc.

**Always:**
1. GET the story first.
2. Build the new `custom_fields` array starting from the existing one.
3. Update or insert only the fields you intend to change.
4. PUT the full merged array.

This is a hard rule. Past incident: an early version of this skill silently wiped Skill Set / Product Area / Priority on 14 tickets, which made them disappear from the dev's filtered board view.

## Flow

### 1. Parse args

- Default `state` to `Ready for deploy` if missing.
- Validate against ENG - Core Workflow states. If unknown, ask via AskUserQuestion; never proceed blindly.

### 2. Refresh repos

```bash
git -C C:/Users/tecno/Desktop/Projects/zng-app fetch --tags --quiet
git -C C:/Users/tecno/Desktop/Projects/zng-admin fetch --tags --quiet
git -C C:/Users/tecno/Desktop/Projects/zng-api fetch --tags --quiet
```

If any fetch fails (dirty tree, auth, etc.), stop and tell the dev. Do not reason against stale state.

Cache the full sorted tag list per repo:

```bash
git -C <repo> tag --sort=creatordate > C:/tmp/tags_<repo>.txt
```

### 3. Discover candidate ticket IDs (pure git author scan)

The candidate set is **every ticket the dev has ever authored a commit for in zng-app or zng-admin** — not Shortcut owner, not assignee history. If the dev wrote code that landed, it counts.

```bash
for repo in C:/Users/tecno/Desktop/Projects/zng-app C:/Users/tecno/Desktop/Projects/zng-admin; do
  git -C "$repo" log --all --author='JosipMuzicZirtue' --pretty='%s' \
    | grep -oE '^[0-9]{5}:' | tr -d ':' | sort -u
done | sort -u > C:/tmp/sc_dev_ticket_ids.txt
```

Convention: subjects start with `<id>:` (e.g. `54109: Sort transactions...`). 5-digit ID, colon, space.

### 4. Filter to the requested workflow state

For each ID in the discovery list, GET `/stories/{id}` and keep only those whose `workflow_state_id` matches the target state.

Cache full story JSON to `C:/tmp/sc_story_<id>.json` — needed in step 5 to preserve existing custom_fields on PUT.

### 5. Categorize by Release value

For each candidate:

- Concrete release (matches `^(FE|Admin) 1\.0\.0\+\d+$` or `^API 1\.0\.\d+$`) — **already set**, but still check other fields (step 7).
- Empty / `Next release` / `TBD` / `Oneday` / `V1.x` — **needs Release backfill** (steps 6 + 7).

### 6. Resolve Release for unset tickets

For each ticket needing Release backfill:

1. **Find merge SHA(s).** Inline mechanical lookup across both Flutter repos:

   ```bash
   for repo in C:/Users/tecno/Desktop/Projects/zng-app C:/Users/tecno/Desktop/Projects/zng-admin; do
     git -C "$repo" log --all --oneline -E --grep="^${id}:"
   done
   ```

   If no `^<id>:` match: also try a broader `--grep "$id"` (catches "X: ... (also Y)" bundles where the secondary id appears in the body).

2. **Confirm SHA is on a deploy branch** (`main` or `develop` — both repos use `develop` as integration; tags get cut from there or after merging to `main`):

   ```bash
   git -C <repo> branch -a --contains <sha>
   ```

3. **Find first version tag containing the SHA** (chronological order):

   ```bash
   git -C <repo> tag --contains <sha> --sort=creatordate
   ```

   First matching `v1.0.0+N` (app/admin) or `v1.0.X` (api) tag wins. Map:
   - `v1.0.0+N` on `zng-app` → `FE 1.0.0+N`
   - `v1.0.0+N` on `zng-admin` → `Admin 1.0.0+N`
   - `v1.0.X` on `zng-api` → `API 1.0.X`

4. **Confidence:**
   - `high` — single repo, unambiguous SHA from `^<id>:` prefix, one matching version tag.
   - `medium` — bundled commit (e.g. `52627: foo (52630)` matched for ticket 52630), or title-keyword fallback.
   - `low` — multiple candidate matches across repos, or only weak signals.

5. **Status:**
   - `resolved` — clear winning tag.
   - `multi-repo` — strong matches in both zng-app and zng-admin; ask dev which is primary.
   - `post-latest-tag` — commit found but not yet in any version tag. Leave as-is.
   - `unmerged` — commit exists but only on a feature branch. Leave as-is.
   - `needs-human` — no commit found at all (rare with the git-author discovery, but possible if dev's git identity changed historically).

### 7. Identify other missing scope fields

For every candidate (whether Release was set or not), check the cached story JSON for missing values among:

- **Skill Set** (default: `Frontend` — value_id `6216069e-e3ed-403b-804c-f678c58b61a7`). Dev is FE; near-universal default.
- **Technical Area** (default by repo: zng-app → `Web App` value_id `6881029c-3921-4900-ad9a-197d3755d25f`; zng-admin → `Admin Portal` value_id `6216069e-e33b-44b0-a3d8-15a130a5a88b`).
- **ZNG: Product Area** (no safe default — infer from ticket name keywords; if unsure, leave blank rather than guess wrong).
- **Priority** (default: `Medium` — value_id `6260361c-7ae3-4d8f-9594-fdff9c39fe4e`).
- **Estimate** (top-level field, not custom): default `1` for trivial bug/sort/copy/event work, `2` for typical bug fix. **Never set >2 silently — always warn the dev with AskUserQuestion before applying any estimate >2.**

### 8. Aggregate + report

Print a markdown table grouped by:

1. Needs Release update (high confidence)
2. Needs Release update (medium/low confidence — flagged)
3. Release already set, but missing other fields
4. `post-latest-tag` / `unmerged` / `needs-human` (no Release update; may still get other-field fills)

For each row include: Story ID, Title, Current Release, Proposed Release, Missing fields, Proposed defaults, Estimate to set (★ if >2, requires confirmation).

### 9. Confirmation gates

**Gate A — Release updates** (AskUserQuestion):
- "Apply all high-confidence Release updates"
- "Apply high + medium"
- "Apply specific story IDs"
- "Skip Release updates"

**Gate B — Estimates >2** (AskUserQuestion, one question per ticket): for each ticket where the proposed estimate is >2, ask the dev to confirm or override.

**Gate C — Other field fills** (AskUserQuestion): bundled gate covering all defaults proposed in step 7 (Skill / Tech / Prod / Priority).

**Gate D — Move to Complete** (AskUserQuestion): "Move all resolved tickets to Complete (workflow state `500018258`)?" — yes / specific subset / no.

Each gate is independent — dev can approve some and skip others.

### 10. Apply updates (preserving existing fields)

For each approved ticket:

```python
# 1. Read existing story JSON (cached from step 4).
existing = json.load(open(f'C:/tmp/sc_story_{sid}.json'))
existing_cfs = {cf['field_id']: cf for cf in existing.get('custom_fields', [])}

# 2. Merge: start from existing, overlay only changed fields.
new_cfs = dict(existing_cfs)  # field_id -> {field_id, value_id, ...}
for change in proposed_changes:  # [{field_id, value_id}, ...]
    new_cfs[change['field_id']] = change  # replace or insert

# 3. PUT the full array.
payload = {'custom_fields': list(new_cfs.values())}
if estimate_to_set is not None:
    payload['estimate'] = estimate_to_set
if move_to_complete:
    payload['workflow_state_id'] = 500018258
```

**Never** PUT a partial `custom_fields` array. **Never** PUT without first having read the existing story.

If the proposed Release label is missing from the enum (e.g. repo has new tag the Shortcut field doesn't list), stop and tell the dev to add the enum value in Shortcut UI first — never invent a new value. (See REST fallback below for fetching the enum.)

### 11. Final summary

Report:
- N Release fields updated
- M other-field fills applied
- K tickets moved to Complete
- L flagged for manual review (unresolved / multi-repo / post-latest-tag)

Include the story URLs for everything updated so the dev can spot-check.

## Shortcut REST quick reference

Token loaded from `~/.claude/.env` (BOM in file, strip with `sed 's/^\xef\xbb\xbf//'`).

```bash
TOKEN=$(grep -a SHORTCUT_API_TOKEN ~/.claude/.env | sed 's/^\xef\xbb\xbf//' | cut -d= -f2 | tr -d '\r\n')

# Get story
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN"

# Search
curl -s "https://api.app.shortcut.com/api/v3/search/stories?query=<urlencoded>&detail=full&page_size=25" -H "Shortcut-Token: $TOKEN"

# Update story
curl -s -X PUT "https://api.app.shortcut.com/api/v3/stories/<id>" \
  -H "Shortcut-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"custom_fields":[...full merged array...],"workflow_state_id":500018258}'

# Get Release enum (uncached — use this if MCP returns stale data)
curl -s "https://api.app.shortcut.com/api/v3/custom-fields/68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb" \
  -H "Shortcut-Token: $TOKEN"
```

## Edge cases

- **Cross-repo fix (zng-app + zng-admin).** Status `multi-repo`. Ask dev which release is primary; Shortcut only allows one Release value per ticket.
- **No commit found.** Status `needs-human`. Don't guess from title alone unless dev opts in.
- **Tag naming drift.** If you see tags that don't match `v1.0.0+N` or `v1.0.X`, flag and stop. Update this skill before proceeding.
- **Enum value missing.** Do not create new enum values via API. Stop with a clear message: "Release enum lacks `<label>`. Add it in Shortcut UI, then re-run."
- **Repo working tree dirty.** `git fetch` still works but never `checkout` anything. This skill only reads tags / log.
- **Estimate already set on ticket.** Never overwrite. Only fill if currently `None`.
- **Existing field already set to wrong value.** Do not "correct" silently. Other-field fills are insert-only — only touch fields that are currently empty.

## What this skill never does

- Never commits in any repo. (Sibling repo rule.)
- Never invents a new Release enum value.
- Never applies updates without explicit approval at each gate.
- Never PUTs a partial `custom_fields` array (would wipe other fields).
- Never overwrites already-set scope fields (Pri/Skill/Prod/Tech/Estimate). Insert-only.
- Never moves a ticket to a workflow state without explicit dev approval (Gate D).
