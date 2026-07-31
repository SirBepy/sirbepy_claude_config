---
name: clockify-reconciliator
description: Triggers on /clockify-reconciliator <project> only. Adds descriptions to description-less Clockify entries for a configured project, splitting large blocks into 1-3h chunks using git commits from configured repos.
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
hubstaff_org_id: <id>    # optional - enables HubStaff comparison step
```

## Steps

### 1. Load config

Read the named file. Abort with clear error listing missing required fields.

**Resolve the Clockify API key here, before any API call:** use the env var named by `api_key_env` if the config sets it, else `CLOCKIFY_API_KEY`. Every Clockify request in steps 4 and 9 sends that value as the `X-Api-Key` header. Getting this wrong does not error loudly - the default key against another account's workspace returns 403 or an empty entry list, which looks exactly like "nothing to reconcile", so state which var you resolved in the run's first output line. If the resolved var is unset, abort and name it.

### 2. HubStaff screenshot preflight (skip if `hubstaff_org_id` not set)

Run before any reconciliation work so the dev can fix auth without waiting through the full reconciliation.

- Resolve the window now: if `[lookback]` was given, parse it; else Monday 00:00 of current week to now, in dev's timezone. (Step 3 will skip resolution if already done here.)
- Compute all Mon-Sun calendar weeks that fall within that window.
- Open Playwright browser. Navigate to the weekly URL for the first week: `https://app.hubstaff.com/organizations/{hubstaff_org_id}/time_entries/weekly?date={mon}&date_end={sun}&filters%5Buser%5D={hubstaff_user_id}`.
- If redirected to `account.hubstaff.com/login`:
  - If `HUBSTAFF_EMAIL`/`HUBSTAFF_PASSWORD` are both set: fill the email/password fields, submit, wait for navigation, then re-check the URL.
    - Still on login page after submit (bad creds, 2FA challenge, CAPTCHA): warn that screenshot step will be skipped, close the tab, continue with reconciliation. Mark screenshot step as "skipped - auto-login failed, may need manual re-login". Tell the dev exactly which weeks would have been screenshotted.
    - Now authenticated: close the tab, continue.
  - If either env var is missing: stop immediately. Tell the dev exactly which weeks would be screenshotted. Wait for manual login in the Playwright window, then re-navigate once.
    - Still on login page after retry: warn that screenshot step will be skipped, close the tab, continue with reconciliation. Mark screenshot step as "skipped - auth failed preflight".
    - Now authenticated: close the tab, continue.
- Not redirected: close the tab, continue.

### 3. Resolve window

If `[lookback]` given, parse it. Else: Monday 00:00 of current week to now, in dev's timezone.

### 4. Fetch Clockify entries

Authenticate with the key resolved in step 1 (`api_key_env` or `CLOCKIFY_API_KEY`), not with `CLOCKIFY_API_KEY` by reflex.

Call `GET /workspaces/{ws}/user/{user}/time-entries?start=...&end=...&page-size=200` — do NOT pass `hydrated=true`, it bloats each entry with full user/project objects. Only fields needed: `id`, `description`, `timeInterval`, `projectId`, `billable`, `tagIds`. Bucket:

- In-project (matches `clockify_project_id`)
- Other-project (for the warning)

### 5. Identify targets

Target = in-project entry with empty or whitespace-only description.

### 6. Read commits

For each repo in config: `git -C <repo> log --author="<user_id or name>" --since=... --until=... --pretty=format:...`. Capture sha, ISO timestamp, subject, body, branch (best-effort via `git branch --contains`).

### 7. Build proposals

For each target:

- Collect ALL dev commits for that calendar day across all configured repos (don't filter by the entry's time window).
- If duration > 3h, plan split into 1-3h chunks (prefer 1h or 2h). Respect original start + end total.
- Distribute the day's commits across chunks by rough chronology: earliest commits → earliest chunks. Assume the dev worked on things in the order committed, even if the commit timestamp falls outside the chunk (e.g. commit at 18:00 can describe the 15:00-17:00 chunk if it represents that chunk's work in the dev's workflow).
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

First exchange the refresh token for an access token - no client credentials needed:
```
POST https://account.hubstaff.com/access_tokens
Body (form-encoded): grant_type=refresh_token&refresh_token=<HUBSTAFF_REFRESH_TOKEN>
```
The response includes a new `refresh_token` - write it back to `HUBSTAFF_REFRESH_TOKEN` in `~/.claude/.env` immediately (token rotates on each exchange).

**Always send a browser `User-Agent` header on `account.hubstaff.com` requests.** That host sits behind Cloudflare, which blocks default library agents (python-urllib, curl) with `403 error code: 1010`. This looks exactly like a revoked token and will send you on a long detour minting a replacement PAT that fails the same way. Use e.g. `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36`.

Exchange once per run and cache the `access_token` (valid 24h). Repeated exchanges return `400 {"error":"rate_limit"}` and lock you out for several minutes.

Fetch HubStaff activity using the returned `access_token`. ALWAYS fetch day-by-day (one request per calendar day) - the activities endpoint paginates at 200 records and a busy week easily exceeds that, silently truncating mid-day. Use `time_slot[start]`/`time_slot[stop]` params (NOT `start_time`/`stop_time`), run all day-requests in parallel:
`GET https://api.hubstaff.com/v2/organizations/{hubstaff_org_id}/activities?time_slot[start]=...&time_slot[stop]=...&user_ids[]={hubstaff_user_id}&page_limit=200`
Use header `Authorization: Bearer <access_token>`.

Response has `activities[]` each with `starts_at` (ISO timestamp) and `tracked` (seconds). To get day boundary: earliest `starts_at` = day start; latest `starts_at + tracked` = day end.

For each calendar day in the window:
- **HubStaff boundary**: earliest `starts_at` and latest `ends_at` across all HubStaff entries that day.
- **Clockify boundary**: earliest start and latest end across all in-project Clockify entries that day (including any just written in step 9).
- **Tolerance**: 10 minutes in either direction.
- Flag the day if `|clockify_start - hubstaff_start| > 10min` OR `|clockify_end - hubstaff_end| > 10min`.

Present flagged days as a table: date, HubStaff window, Clockify window, which boundary is off and by how much. Days within tolerance: show as green/OK in a summary line.

Do NOT auto-fix anything here - report only. User decides what to adjust.

### 12. HubStaff weekly screenshot (skip if `hubstaff_org_id` not set or preflight marked auth as failed)

Auth already confirmed in step 2 - no login-check needed here. For each Mon-Sun week computed in step 2:

- Navigate to `https://app.hubstaff.com/organizations/{hubstaff_org_id}/time_entries/weekly?date={mon}&date_end={sun}&filters%5Buser%5D={hubstaff_user_id}` (dates as `YYYY-MM-DD`).
- Resize viewport to ~1600x1000 before screenshotting so the weekly table renders wide enough.
- Wait for the weekly data grid to render: use `browser_wait_for` targeting a table row or data cell that indicates the grid has loaded (timeout 10s). If timeout: warn "weekly table did not load for {mon} - skipping this week's screenshot" and move to the next week.
- Take screenshot: `browser_take_screenshot` with `fullPage: false`, filename `hubstaff-weekly-{mon}_to_{sun}.png` (relative path - playwright MCP can only write under its allowed roots).
- Validate file size: if the saved file is under 50 KB, warn "screenshot for {mon} may be a login page or empty table - check manually before sharing."
- Move the file to `C:\Users\tecno\Desktop\`.
- Close the browser tab.

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
