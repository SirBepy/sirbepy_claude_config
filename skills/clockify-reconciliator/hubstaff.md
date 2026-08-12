# clockify-reconciliator — HubStaff steps

Read this file at steps 2, 11, and 12 of the main skill flow whenever `hubstaff_org_id` is set in the project config. Also read the "HubStaff update mode" section (between Step 11 and Step 12) whenever the dev asks to update/sync HubStaff rather than just compare. Skip this file entirely otherwise.

## Step 2 — HubStaff screenshot preflight (skip if `hubstaff_org_id` not set)

Run before any reconciliation work so the dev can fix auth without waiting through the full reconciliation.

- Resolve the window now (see step 3 in SKILL.md for the parsing rules).
- Compute all Mon-Sun calendar weeks that fall within that window.
- Kill any orphaned browser holding the HubStaff profile dir before opening a new one: `Get-CimInstance
  Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -match 'playwright-profiles.hubstaff' } | Stop-Process -Force`.
  A prior run's browser left open on this profile makes the next launch fail with a misleading "Target
  closed" error instead of a real one (see `reference_playwright_orphan_profile_lock.md`).
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
The response includes a new `refresh_token` (token rotates on each exchange - the OLD value is now
worthless the instant this call succeeds, it's single-use). Write it back with a backup-first sequence:

1. Copy the CURRENT full content of `~/.claude/.env` to `~/.claude/.env.bak` (whole file, not just
   the token line).
2. Only after that write succeeds, replace the `HUBSTAFF_REFRESH_TOKEN=` line in `~/.claude/.env`.
3. If either write fails (permission error, disk full, etc.): STOP, do not retry the exchange (the
   old token is already invalidated so a retry fails the same way), and tell the dev the new token
   value directly so it can be saved manually.

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

## HubStaff update mode (dev asks to "update/sync HubStaff" after a run)

Distinct from the read-only comparison above - this is for when the dev asks Claude to write entries
into HubStaff, not just report on drift.

- **Scope default is the FULL reconciled window**, not just entries created/edited this run. Ask via
  AskUserQuestion with the full window as the recommended option:
  - "Full window (N entries, recommended - matches Clockify)"
  - "Just the days touched this run (M entries, partial - opt-in only)"
- **Billable** (`[data-testid="time-entries-form-dialog-billable"]`) is a SEPARATE flag from Clockify's,
  which is always false by convention - don't silently reuse that here, ask if unclear. Confirmed dev
  default 2026-08-10: unchecked.
- **Entry creation recipe** (Add-time dialog, scoped to `.modal-content:visible`):
  - Project and Reason: `selectOption(value)` on the hidden `select2-hidden-accessible` `<select>`
    (`modal.locator('select').nth(0)` for Project, `.nth(2)` for Reason). Never `.click()` the rendered
    Reason span - it silently lands on the wrong option without showing a list.
  - Time fields: `.from-hour-select`/`.to-hour-select` -> `input.default-input` typed value +
    `.meridiem-toggle` click.
  - Note: click `a:has-text("Add note")`, then fill `textarea[name="work_note"]`.
  - Save: `button.save-button:has-text("Save")`; `.modal-content:visible` count hitting 0 confirms it.
  - Full field-by-field detail and edge cases: `reference_hubstaff_ui_time_edit.md` (zng-app project
    memory).

## Step 12 — HubStaff weekly screenshot (skip if `hubstaff_org_id` not set or preflight marked auth as failed)

Auth already confirmed in step 2 - no login-check needed here. Same orphan-browser guard as step 2
applies before opening the browser here too. For each Mon-Sun week computed in step 2:

- Navigate to `https://app.hubstaff.com/organizations/{hubstaff_org_id}/time_entries/weekly?date={mon}&date_end={sun}&filters%5Buser%5D={hubstaff_user_id}&filters%5BshowWeeklycopy%5D=` (dates as `YYYY-MM-DD`). The `showWeeklycopy` param is required - without it the Total column renders differently.
- Resize viewport to width >= 2300 (height ~1000), then click the left-nav collapse toggle (element
  with text `left_panel_close`) so the grid gets full width. At ~1600 wide the rightmost **Total**
  column sits behind a horizontal scrollbar and is unreadable in the screenshot.
- Wait for the weekly data grid to render: use `browser_wait_for` targeting a table row or data cell that indicates the grid has loaded (timeout 10s). If timeout: warn "weekly table did not load for {mon} - skipping this week's screenshot" and move to the next week.
- Take screenshot: `browser_take_screenshot` with `fullPage: false`, clipped to the grid region (not
  the whole page - there's empty space below the two data rows), filename
  `hubstaff-weekly-{mon}_to_{sun}.png` (relative path - playwright MCP can only write under its allowed roots).
- Validate file size: if the saved file is under 50 KB, warn "screenshot for {mon} may be a login page or empty table - check manually before sharing."
- Move the file to `C:\Users\tecno\Desktop\`.
- Close the browser tab.

To READ exact per-slot time boundaries when verifying alignment (not for the screenshot itself), use
the Calendar view instead: `https://app.hubstaff.com/organizations/{hubstaff_org_id}/time_entries/calendar?date={mon}&date_end={sun}&filters%5Buser%5D={hubstaff_user_id}`.
