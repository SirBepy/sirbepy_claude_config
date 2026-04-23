---
name: zirtue-release-backfill
description: Triggers on /zirtue-release-backfill only. For Shortcut tickets assigned to the dev whose Release field is unset / Next release / TBD, figures out the real release (FE/Admin/API version) by matching merge SHAs against git tags across zng-app, zng-admin, zng-api, reports findings, and applies updates only after the dev approves.
---

# /zirtue-release-backfill

> Backfill the Shortcut **Release** custom field on the dev's tickets by correlating the fix's merge SHA with release tags in the right repo. Always report first, apply only after explicit approval.

## Why this skill exists

- Tickets move to `Ready for deploy` (or `Complete`) without a concrete Release value set. PM wants it populated so deploy notes / release summaries are accurate.
- The mapping is mechanical but spread across three repos and Shortcut's enum values. Easy to get wrong by hand across 15+ tickets.
- Running it as a skill keeps the procedure consistent every time the dev wants to do a pass.

## Args

```
/zirtue-release-backfill [state]
```

- `state` (optional) — Shortcut workflow state name to filter on. Default: `Ready for deploy`. Examples: `Complete`, `Testing`, `PR Review`.
- If the dev passes an unknown state, ask with AskUserQuestion listing the actual state names from `workflows-list` (`ENG - Core Workflow`).

Owner is always the dev (`josipmui`). Not configurable here — if the dev wants someone else's tickets he'll say so explicitly and we add it later.

## Required tools

- `mcp__shortcut__stories-search` — fetch candidate tickets
- `mcp__shortcut__stories-get-by-id` with `full: true` — read custom_fields + linked PRs/commits/branch
- `mcp__shortcut__stories-get-branch-name` — get the generated branch string for git lookups
- `mcp__shortcut__custom-fields-list` — resolve Release value IDs. **Caveat:** this endpoint is aggressively cached on the MCP side. If the dev just added a new enum value in the Shortcut UI and it doesn't show up, fall back to the REST API (see "MCP cache workaround" below).
- `mcp__shortcut__stories-update` — apply the Release field (only after approval). The `shortcut-create-ticket` guard hook (`~/.claude/skills/shortcut-create-ticket/hooks/guard_mutation.py`) has a release-only bypass — mutations that touch **only** `custom_fields[Release]` skip the `requested_by_id == owner` check so this skill can update tickets filed by teammates. If you see `SHORTCUT_OWNER_UUID not set` or `refusing to mutate` errors for Release-only updates, the bypass is broken — fix the hook, don't work around it.
- `Bash` — git tag / log / fetch in the three repos
- `Agent` (`general-purpose`) — one subagent per ticket, parallel batches

## Fixed identity & constants

Never re-derive:

- Dev user ID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Mention name: `josipmui`
- Release custom field ID: `68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb`
- Sentinel Release values (skip-investigation list):
  - `Next release` — value_id `698b4bce-ecd7-44c3-b62a-2b49b2506c1d`
  - `TBD` — value_id `698b510b-c54a-4adb-b47f-93a06852afe1`
  - `Oneday` — value_id `69247286-4a0c-4fcf-a3c4-85f8bf6af1ea`
  - `V1.0`, `V1.1`, `V2.0` — legacy placeholders, treat as unset for backfill purposes
- Repos (sibling paths from zng-app root):
  - `zng-app` — Flutter web consumer app. Tag format: `v1.0.0+N` (build) + `Release-MM-DD-YYYY` (deploy). Shortcut label: `FE 1.0.0+N`.
  - `../zng-admin` — Flutter web admin. Tags `v1.0.0+N` + `Release-MM-DD-YYYY`. Shortcut label: `Admin 1.0.0+N`.
  - `../zng-api` — NestJS backend. Tags `v1.0.X`. Shortcut label: `API 1.0.X`.

## Flow

### 1. Parse args

- Default `state` to `Ready for deploy` if missing.
- Validate against `ENG - Core Workflow` states (workflow id `500018252`). If unknown, ask with AskUserQuestion; never proceed blindly.

### 2. Fetch candidate tickets

`stories-search` with `owner: "me"`, `state: "<state>"`, `isArchived: false`. Record all story IDs.

### 3. Filter down

For each story, look at the current Release value:

- If the value is a concrete release label (matches regex `^(FE|Admin) 1\.0\.0\+\d+$` or `^API 1\.0\.\d+$`) — **skip**. Log it in the final report under "already set, not re-verified".
- If value is empty / `Next release` / `TBD` / `Oneday` / `V1.0` / `V1.1` / `V2.0` — **investigate**.

### 4. Refresh repos

Before dispatching subagents, in the main agent:

```bash
git -C . fetch --tags --quiet
git -C ../zng-admin fetch --tags --quiet
git -C ../zng-api fetch --tags --quiet
```

If any `fetch` fails (dirty tree, auth, etc.), stop and tell the dev. Do not reason against stale state.

Also cache the full sorted tag list per repo once so subagents don't each re-run it:

```bash
git -C <repo> tag --sort=creatordate
```

Pass those lists to each subagent in the prompt. Cuts down on duplicate git calls.

### 5. Dispatch subagents (one per ticket, parallel batches of ~6)

Use `Agent` tool, `subagent_type: general-purpose`. Include in every prompt:

- Story ID
- Story title + description + linked PRs/commits + branch name (already fetched by main agent, no re-fetch)
- The three cached tag lists
- The Release label conventions (FE/Admin/API → repo mapping)
- Repo paths (`zng-app`, `../zng-admin`, `../zng-api`) resolved to absolute paths
- Explicit **read-only** directive — subagents MUST NOT call `stories-update`
- Output contract (strict JSON in their final message):

```json
{
  "story_id": 12345,
  "candidates": [
    {
      "repo": "zng-app",
      "merge_sha": "abc1234",
      "first_release_tag": "v1.0.0+48",
      "first_deploy_tag": "Release-4-14-2026",
      "proposed_release_label": "FE 1.0.0+48",
      "confidence": "high"
    }
  ],
  "status": "resolved | unmerged | post-latest-tag | multi-repo | needs-human",
  "notes": "short human-readable summary"
}
```

### 6. Per-ticket subagent procedure (documented here so the prompt stays short)

1. Identify target repo(s) from Technical Area / Product Area / branch prefix / linked PR URL (repo is usually in the URL). Multi-repo is valid.
2. Find merge SHA:
   - Prefer the merge commit from the linked PR.
   - Fall back to `git log --all --grep="sc-<story_id>"` across all three repos (use `-i` for case).
   - Fall back to branch name from `stories-get-branch-name`: `git log --all --grep="<branch-name>"`.
3. Confirm the SHA is on the repo's default branch (`main` or `develop` — check which the repo uses) with `git branch --contains <sha>`. If not on main, set `status: unmerged`.
4. Run `git -C <repo> tag --contains <sha> --sort=creatordate`. First matching `v1.0.0+N` (app/admin) or `v1.0.X` (api) tag wins.
5. Map tag → Shortcut label:
   - `v1.0.0+N` on `zng-app` → `FE 1.0.0+N`
   - `v1.0.0+N` on `zng-admin` → `Admin 1.0.0+N`
   - `v1.0.X` on `zng-api` → `API 1.0.X`
6. Confidence rules:
   - `high` — one repo, unambiguous SHA, one matching tag.
   - `medium` — ambiguous SHA match (multiple candidate merges) or branch name fuzzy-matched.
   - `low` — fell back to title keyword search or touched multiple repos.
7. If no tag contains the SHA → `status: post-latest-tag`, leave Release as-is (still `Next release`).
8. Return the JSON payload. Nothing else.

### 7. Aggregate + report

Main agent collects all JSON payloads and prints a markdown table:

```
| Story | Title | Current | Repo | SHA | Tag | Proposed | Confidence | Notes |
```

Group by: needs-update (high confidence) → needs-update (medium/low) → post-latest-tag → unmerged / needs-human → already-set (skipped).

### 8. Gate: wait for approval

Use AskUserQuestion with options:

- "Apply all high-confidence" — updates only rows marked `high`.
- "Apply all except flagged" — updates high + medium; leaves low / multi-repo / needs-human.
- "Apply specific rows" — dev picks story IDs in a follow-up.
- "Cancel, report only" — no updates.

Never auto-apply without this gate, even for obvious cases.

### 9. Apply updates

For each approved row, call `stories-update`:

```json
{
  "id": <story_id>,
  "custom_fields": [
    { "field_id": "68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb", "value_id": "<release-value-id>" }
  ]
}
```

Resolve `<release-value-id>` from `custom-fields-list`. If the proposed label isn't in the enum (e.g. the repo has a new tag the Shortcut field doesn't list yet), stop and tell the dev to add the enum value in Shortcut UI first — never invent a new release value.

### 10. Final summary

Report: `N updated, M skipped, K flagged for manual review`. Include the story URLs of updated ones so the dev can spot-check.

## MCP cache workaround (REST fallback)

`mcp__shortcut__custom-fields-list` can return stale data for several minutes after the dev adds an enum value in the Shortcut UI. When you need a freshly-added Release value ID, hit the REST API directly — it is not cached.

```bash
source ~/.claude/.env && curl -s \
  "https://api.app.shortcut.com/api/v3/custom-fields/68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb" \
  -H "Shortcut-Token: $SHORTCUT_API_TOKEN" \
  | python -c "import sys,json; d=json.load(sys.stdin); [print(v['value'],v['id']) for v in d['values']]"
```

(`68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb` is the Release custom field UUID — hardcoded in Fixed identity & constants above.) Use this whenever MCP returns an older snapshot.

## Edge cases

- **Cross-repo fix (FE + API).** Report both rows, ask which is the "primary" release to set on the ticket. Shortcut only allows one Release value per ticket; don't try to pick silently.
- **Story has no branch / no PR / no commit metadata.** Status `needs-human`. Don't guess from title alone at high confidence.
- **Tag naming drift.** If you see tags that don't match `v1.0.0+N` or `v1.0.X`, flag the repo's tag scheme has changed and stop. Update this skill before proceeding.
- **Enum value missing.** Do not create new enum values. Stop with a clear message: "Release enum lacks `FE 1.0.0+49`. Add it in Shortcut UI, then re-run."
- **Repo working tree dirty.** `git fetch` still works but be careful not to `checkout` anything. This skill only reads tags / log; never checks out.

## What this skill never does

- Never commits in any repo. (Sibling repo rule.)
- Never changes workflow state, owner, iteration, epic, or any custom field besides Release.
- Never invents a new Release enum value.
- Never applies updates without explicit approval.
- Never dispatches more subagents than tickets to investigate (1-per-ticket hard cap).
