---
name: clockify-reconciliator
description: Adds descriptions to description-less Clockify entries for a configured project, splitting large blocks into 1-3h chunks using git commits from configured repos.
disable-model-invocation: true
argument-hint: <project-name> [lookback]
---

# /clockify-reconciliator

> Fill empty Clockify descriptions from git commits.

## Inputs

- `<project-name>` (required): matches `~/.claude/skills/clockify-reconciliator/projects/<project-name>.md`.
- `[lookback]` (optional): overrides default window. Accepted values:
  - `today` - today only (dev timezone)
  - `yesterday` - yesterday only (dev timezone)
  - `past-N-weeks` or `past-N-days` - rolling window ending now
  - `YYYY-MM-DD..YYYY-MM-DD` - explicit date range
  - Default if omitted: current work week (Mon to today, dev timezone).

## Prereqs

- Clockify API key env var set (or present in `~/.claude/.env`). Uses `api_key_env` from the project config if set, else defaults to `CLOCKIFY_API_KEY`.
- If project config has `hubstaff_org_id` set: `HUBSTAFF_REFRESH_TOKEN` must be present in `~/.claude/.env`. If missing, skip HubStaff comparison and warn.
- For the screenshot preflight auto-login (step 2): `HUBSTAFF_EMAIL` and `HUBSTAFF_PASSWORD` in `~/.claude/.env`. If either is missing, fall back to manual login (wait for the dev in the Playwright window) instead of auto-filling.
- Project config file exists. If missing, print the template below and abort.

## Project config template

Path: `~/.claude/skills/clockify-reconciliator/projects/<name>.md`

```
clockify_workspace_id: <id>
clockify_project_id: <id>
clockify_project_name: <display>
user_id: <clockify user id>
api_key_env: CLOCKIFY_API_KEY   # optional, default CLOCKIFY_API_KEY - set to a different var name for accounts other than the default Cinnamon one
repos:
  - /abs/path/to/repo-1
  - /abs/path/to/repo-2
ticket_regex: (sc-\d+)   # optional, default (sc-\d+)|(#\d+)
hubstaff_org_id: <id>       # optional - enables HubStaff comparison step
hubstaff_user_id: <id>      # required if hubstaff_org_id is set - interpolated into the HubStaff URLs/filters
```

## Steps

### 1. Load config

Read the named file. Abort with clear error listing missing required fields.

**Resolve the Clockify API key here, before any API call:** use the env var named by `api_key_env` if the config sets it, else `CLOCKIFY_API_KEY`. Every Clockify request in steps 4 and 9 sends that value as the `X-Api-Key` header. Getting this wrong does not error loudly - the default key against another account's workspace returns 403 or an empty entry list, which looks exactly like "nothing to reconcile", so state which var you resolved in the run's first output line. If the resolved var is unset, abort and name it.

### 2. HubStaff screenshot preflight (skip if `hubstaff_org_id` not set)

If `hubstaff_org_id` is set, read `skills/clockify-reconciliator/hubstaff.md` now and follow its "Step 2" section before any reconciliation work, so the dev can fix auth without waiting through the full run.

### 3. Resolve window

If `[lookback]` given, parse it. Else: Monday 00:00 of current week to now, in dev's timezone.

For a single-day lookback (`today`, `yesterday`, or an explicit single `YYYY-MM-DD`), the window is always a full local calendar day, true midnight-to-midnight: `<day> 00:00:00` to `<day+1> 00:00:00`, dev's timezone. `today` = the current calendar date; `yesterday` = current calendar date minus 1 calendar day. Compute the calendar date first, then take that date's midnight-to-midnight span - never derive the boundary as "now minus 24h", and never use a rounded/approximate cutoff (e.g. `22:00`) in place of true midnight. This window feeds both the Clockify entry fetch (step 4) and the git-log bounds (step 6). See `~/.claude/projects/c--Users-tecno-Desktop-Projects-zng-app/memory/feedback_verify_date_calculations.md` for the 2026-07-28 incident this rule fixes.

### 4. Fetch Clockify entries

Authenticate with the key resolved in step 1 (`api_key_env` or `CLOCKIFY_API_KEY`), not with `CLOCKIFY_API_KEY` by reflex.

Call `GET /workspaces/{ws}/user/{user}/time-entries?start=...&end=...&page-size=200` — do NOT pass `hydrated=true`, it bloats each entry with full user/project objects. Only fields needed: `id`, `description`, `timeInterval`, `projectId`, `billable`, `tagIds`. Bucket:

- In-project (matches `clockify_project_id`)
- Other-project (for the warning)

### 5. Identify targets

Target = in-project entry with empty or whitespace-only description.

### 6. Read commits

For each repo in config: `git -C <repo> log --author="<user_id or name>" --since=... --until=... --pretty=format:...`, using the window resolved in step 3. Capture sha, ISO timestamp, subject, body, branch (best-effort via `git branch --contains`).

Then run one more pass per repo covering the first 4 hours after the window's END: `--since="<end>" --until="<end> + 4h"`. For a single-day lookback that is `<day+1> 00:00:00` to `<day+1> 04:00:00`; for a multi-day range it is the same 4 hours past the range's final midnight. Flag hits as "late-night spillover from <last day in window>" and split them across the boundary by each commit's real wall-clock minutes on its own calendar day. Never drop them, never fold the whole session onto one side.

### 7. Build proposals

For each target:

- Collect ALL dev commits for that calendar day across all configured repos (don't filter by the entry's time window).
- If duration > 3h, plan split into 1-3h chunks (prefer 1h or 2h). Respect original start + end total.
- Distribute the day's commits across chunks by rough chronology: earliest commits → earliest chunks. Assume the dev worked on things in the order committed, even if the commit timestamp falls outside the chunk (e.g. commit at 18:00 can describe the 15:00-17:00 chunk if it represents that chunk's work in the dev's workflow).
- Round every chunk boundary (start and end, including the overall entry's original start/end) to the nearest 5-minute mark (:00/:05/:10/.../:55), seconds always :00. Round the shared boundary between adjacent chunks once and reuse that value as both the earlier chunk's end and the later chunk's start, so rounding never introduces a gap or overlap. Do this before presenting the plan in step 9, not after approval.
- Draft description from the chunk's assigned commit subjects. Max 80 chars. Drop filler to fit.
- If a matched commit subject hits `ticket_regex`, strip the matched ticket prefix from the description body (don't repeat it in the text) and append ` (53794)` using just the captured number, once, at the end only. Never leave the ticket number both leading the body and trailing in parens.
- **Never use the same description verbatim on two chunks.** If all commits land in one chunk leaving others empty, split the description on semicolons: assign the pre-semicolon part to the first chunk and the post-semicolon part(s) to the remaining chunk(s). If there are more chunks than semicolon-delimited parts, the last non-ticket part fills the extras.
- If a day has zero commits at all across all repos, ask the dev what was done before proposing.

### 8. Warn on other-project entries

List description-less entries in OTHER projects in the same window. Dev handles those separately (could be a different config).

### 9. Present plan

Show a table: date, start-end, duration, proposed split, proposed description(s). Use AskUserQuestion:

- Apply all
- Apply some (pick which by index)
- Cancel

### 10. Apply

Approved rows only.

- Description-only: `PUT /workspaces/{ws}/time-entries/{id}` with updated description, preserving start/end/project/billable/tags.
- Split: shorten the original to the first chunk's end, then `POST /workspaces/{ws}/time-entries` for each remaining chunk with same project, same tags, contiguous times.

### 11. HubStaff comparison (skip if `hubstaff_org_id` not set or `HUBSTAFF_REFRESH_TOKEN` missing)

If gated in, read `skills/clockify-reconciliator/hubstaff.md` and follow its "Step 11" section.

### 12. HubStaff weekly screenshot (skip if `hubstaff_org_id` not set or preflight marked auth as failed)

If gated in, read `skills/clockify-reconciliator/hubstaff.md` and follow its "Step 12" section.

### 13. Report

- Entries written (count + per-day summary)
- HubStaff comparison results (step 11), or "HubStaff comparison skipped - hubstaff_org_id not configured" if absent
- HubStaff weekly screenshot path(s) (step 12), or skipped reason (auth failed preflight / org not configured)
- "Needs manual" targets with time + reason
- Other-project warning list

## Rules

- Never touch an entry that already has a non-empty description.
- Never create entries in empty time ranges. Only operate on existing entries (splits allowed).
- Max 80 chars per description.
- Ticket suffix only if a matched commit carries one. One ticket per description, most relevant. Number appears once, in parens, at the end - never repeated as a leading prefix too.
- No em dashes. Commas or hyphens.
- Every entry's start and end time, written or created, lands on a 5-minute mark with :00 seconds. Never a raw commit-derived minute (18:56, 22:12, etc).
