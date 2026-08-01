# clockify-reconciliator — HubStaff steps

Read this file at steps 2, 11, and 12 of the main skill flow whenever `hubstaff_org_id` is set in the project config. Skip this file entirely otherwise.

## Step 2 — HubStaff screenshot preflight (skip if `hubstaff_org_id` not set)

Run before any reconciliation work so the dev can fix auth without waiting through the full reconciliation.

- Resolve the window now (see step 3 in SKILL.md for the parsing rules).
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

## Step 11 — HubStaff comparison (skip if `hubstaff_org_id` not set or `HUBSTAFF_REFRESH_TOKEN` missing)

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

## Step 12 — HubStaff weekly screenshot (skip if `hubstaff_org_id` not set or preflight marked auth as failed)

Auth already confirmed in step 2 - no login-check needed here. For each Mon-Sun week computed in step 2:

- Navigate to `https://app.hubstaff.com/organizations/{hubstaff_org_id}/time_entries/weekly?date={mon}&date_end={sun}&filters%5Buser%5D={hubstaff_user_id}` (dates as `YYYY-MM-DD`).
- Resize viewport to ~1600x1000 before screenshotting so the weekly table renders wide enough.
- Wait for the weekly data grid to render: use `browser_wait_for` targeting a table row or data cell that indicates the grid has loaded (timeout 10s). If timeout: warn "weekly table did not load for {mon} - skipping this week's screenshot" and move to the next week.
- Take screenshot: `browser_take_screenshot` with `fullPage: false`, filename `hubstaff-weekly-{mon}_to_{sun}.png` (relative path - playwright MCP can only write under its allowed roots).
- Validate file size: if the saved file is under 50 KB, warn "screenshot for {mon} may be a login page or empty table - check manually before sharing."
- Move the file to `C:\Users\tecno\Desktop\`.
- Close the browser tab.
