# clockify-reconciliator - HubStaff steps

Read this file at steps 2, 11, and 12 of the main skill flow whenever `hubstaff_org_id` is set in the project config. Also read the "HubStaff update mode" section (between Step 11 and Step 12) whenever the dev asks to update/sync HubStaff rather than just compare. Skip this file entirely otherwise.

## Step 2 - HubStaff screenshot preflight (skip if `hubstaff_org_id` not set)

Run before any reconciliation work so the dev can fix auth without waiting through the full reconciliation.

**Dependency: local Playwright, not a Playwright MCP server.** This step and step 12 drive the
npx-cached `playwright` package directly via `skills/clockify-reconciliator/scripts/hs_preflight.cjs`
and `hs_weekshot.cjs` (Node, headed Chromium, persistent profile). No MCP browser tool is required or
assumed - do not wait for `browser_wait_for`/`browser_take_screenshot` to appear in the tool list. See
`reference_local_playwright_fallback` for why this is the default over an MCP server.

- Resolve the window now (see step 3 in SKILL.md for the parsing rules).
- Compute all Mon-Sun calendar weeks that fall within that window.
- Kill any orphaned browser holding the HubStaff profile dir before opening a new one: `Get-CimInstance
  Win32_Process -Filter "Name='chrome.exe'" | Where-Object { $_.CommandLine -match 'playwright-profiles.hubstaff' } | Stop-Process -Force`.
  A prior run's browser left open on this profile makes the next launch fail with a misleading "Target
  closed" error instead of a real one (see `reference_playwright_orphan_profile_lock.md`).
- Run `node skills/clockify-reconciliator/scripts/hs_preflight.cjs --org {hubstaff_org_id} --user
  {hubstaff_user_id} --profile skills/clockify-reconciliator/playwright-profiles/hubstaff --mon {mon}
  --sun {sun}` for the first week, with `HUBSTAFF_EMAIL`/`HUBSTAFF_PASSWORD` set in the process env if
  present. The script prints one JSON line: `{"authOk":true}` or `{"authOk":false,"reason":"..."}`.
  - `authOk:false`, reason mentions auto-login: warn that the screenshot step will be skipped, mark it
    "skipped - auto-login failed, may need manual re-login". Tell the dev exactly which weeks would
    have been screenshotted, then continue with reconciliation.
  - `authOk:false`, reason mentions manual login timeout: the script waited 120s in the visible browser
    window for the dev to log in by hand and gave up. Mark the screenshot step "skipped - auth failed
    preflight", tell the dev which weeks would have been screenshotted, then continue.
  - `authOk:true`: continue, auth confirmed for step 12.

## Step 11 - HubStaff comparison (skip if `hubstaff_org_id` not set or `HUBSTAFF_REFRESH_TOKEN` missing)

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

**Per-entry completeness pass, in addition to the whole-day boundary check above.** The boundary check
alone misses internal gaps and misattributes midnight-spanning entries: a session split into two
Clockify entries at midnight can make the second calendar day look like it "starts at 00:00" when the
real gap, if any, is inside that day's own tail chunk. For every Clockify entry in the window,
including each half of one that spans midnight, confirm HubStaff has some tracked or manual coverage
overlapping that entry's exact window. Flag any Clockify entry with zero overlapping HubStaff coverage
as a per-entry gap, listed separately from the whole-day boundary flags above - a day can pass the
boundary check and still hide one of these.

**Before reporting any day as matching/aligned, re-fetch both sides live in this same pass.** Never
reuse a Clockify or HubStaff fetch from earlier in the run, or a scratch file, without confirming its
timestamp is from this pass - a stale read is indistinguishable from a real match otherwise.

Do NOT auto-fix anything here - report only. User decides what to adjust.

## HubStaff update mode (dev asks to "update/sync HubStaff" after a run)

Distinct from the read-only comparison above - this is for when the dev asks Claude to write entries
into HubStaff, not just report on drift. Only offer this mode when step 11 (whole-day or per-entry)
flagged something outside tolerance - never run it unprompted.

- **Scope default is the FULL reconciled window**, not just entries created/edited this run. Ask via
  AskUserQuestion with the full window as the recommended option:
  - "Full window (N entries, recommended - matches Clockify)"
  - "Just the days touched this run (M entries, partial - opt-in only)"
- **Proposed-edit table, always required before any mutation** (matches step 9's discipline): one row
  per flagged item, columns date, case (`add missing` / `edit boundary` / `trim excess`), current
  HubStaff window, target Clockify window, Reason value to be set. Get AskUserQuestion approval - Apply
  all / Apply some (pick which by index) / Cancel - before touching HubStaff. Prefer **Edit time
  entry** over delete-then-recreate; use **Add time** only when Clockify has more blocks that day than
  HubStaff; use **trim** (see below) only when HubStaff has more tracked time than Clockify.
- **Billable** (`[data-testid="time-entries-form-dialog-billable"]`) is a SEPARATE flag from Clockify's,
  which is always false by convention - don't silently reuse that here, ask if unclear. Confirmed dev
  default 2026-08-10: unchecked.
- **Reason defaults to `Forgot to start/stop timer`** on add/edit, surfaced in the approval table since
  it's client-visible audit metadata - never silently applied without the dev seeing it.
- **Add missing** (Add-time dialog, scoped to `.modal-content:visible`):
  - Project and Reason: `selectOption(value)` on the hidden `select2-hidden-accessible` `<select>`
    (`modal.locator('select').nth(0)` for Project, `.nth(2)` for Reason). Never `.click()` the rendered
    Reason span - it silently lands on the wrong option without showing a list.
  - Time fields: `.from-hour-select`/`.to-hour-select` -> `input.default-input` typed value +
    `.meridiem-toggle` click. Reuse the source Clockify entry's exact start/end verbatim (already
    5-minute aligned) rather than re-deriving or rounding independently.
  - Note: click `a:has-text("Add note")`, then fill `textarea[name="work_note"]`.
  - Save: `button.save-button:has-text("Save")`; `.modal-content:visible` count hitting 0 confirms it.
- **Edit boundary**: row Actions menu (hover the row, `a.dropdown-toggle:has-text("Actions")`) ->
  **Edit time entry**. Same modal shape and field recipe as Add missing above; set the time fields to
  the target Clockify window instead of leaving the existing HubStaff times.
- **Trim excess**: HubStaff has MORE tracked time than Clockify for that window (e.g. an automatic
  tracker ran through an unlogged break) - not a gap, the opposite direction. Row Actions -> **Split
  time entry** -> **DELETE TIME** tab, set a FROM/TO sub-range inside the tracked block bounding just
  the excess slice. Its Reason field is a free-text `<textarea>`, not the select2 dropdown Add/Edit use.
  Never use Edit or delete-then-recreate for this case, it drops the untouched part of the entry.
- **Verify after each mutation via the API** (step 11's activities fetch), not by trusting the UI's own
  confirmation toast. Remember the single-exchange/rate-limit rule on the access-token endpoint.
  - Full field-by-field detail and edge cases for all three cases: `reference_hubstaff_ui_time_edit.md`
    (zng-app project memory) - this section only covers entry points, not the full selector recipe.

## Step 12 - HubStaff weekly screenshot (skip if `hubstaff_org_id` not set or preflight marked auth as failed)

Auth already confirmed in step 2 - no login-check needed here. Same orphan-browser guard as step 2
applies before opening the browser here too.

Run `node skills/clockify-reconciliator/scripts/hs_weekshot.cjs --org {hubstaff_org_id} --user
{hubstaff_user_id} --profile skills/clockify-reconciliator/playwright-profiles/hubstaff --weeks
{mon1}:{sun1},{mon2}:{sun2},... --out-dir C:/Users/tecno/Desktop` with all Mon-Sun weeks computed in
step 2 (dates as `YYYY-MM-DD`). The script navigates each week (with the required `showWeeklycopy`
param, resizes the viewport to >= 2300 wide, and collapses the left nav so the **Total** column isn't
behind a scrollbar), waits up to 10s for the grid to render, and writes
`hubstaff-weekly-{mon}_to_{sun}.png` straight to `--out-dir` - no relative-path-then-Move-Item dance,
a local script has no write-root restriction. It prints one JSON array line, one object per week:
`{mon, sun, path, sizeBytes, warning}` (`warning` set and `path`/`sizeBytes` absent if the grid never
loaded; `warning` set alongside `path` if the file saved under 50 KB, which usually means a login page
or empty table). Report any `warning` to the dev instead of treating that week's screenshot as done.

To READ exact per-slot time boundaries when verifying alignment (not for the screenshot itself), use
the Calendar view instead: `https://app.hubstaff.com/organizations/{hubstaff_org_id}/time_entries/calendar?date={mon}&date_end={sun}&filters%5Buser%5D={hubstaff_user_id}`.

## hs_addtime.cjs - bulk Add-time

**Status: validated 2026-08-21.** First live run wrote 21 entries (30h) to the zirtue project,
verified via the activities API and the weekly-screenshot total afterward - all 21 reported
`ok:true` and matched. The shape below is confirmed working, not just intended.

Bulk-writes HubStaff time entries via the web UI Add-time dialog (the v2 API is read-only for
time), one entry per call to `skills/clockify-reconciliator/scripts/hs_addtime.cjs`. Only offer
this inside "HubStaff update mode" above, for the "Add missing" case, and only after the dev has
seen and approved the proposed-edit table.

Entries file shape, one object per HubStaff entry to create:
```json
[{"date": "YYYY-MM-DD", "from": "9:00 am", "to": "11:30 am", "note": "..."}]
```

Run `node skills/clockify-reconciliator/scripts/hs_addtime.cjs --org {hubstaff_org_id} --user
{hubstaff_user_id} --profile skills/clockify-reconciliator/playwright-profiles/hubstaff --entries
<path-to-json> --project-label {hubstaff_project_label} --reason-label {hubstaff_reason_label}`.
`--project-label` is required (project config field `hubstaff_project_label`, same source as
`hubstaff_org_id`/`hubstaff_user_id` - never hardcode an account's project name here).
`--reason-label` is optional, defaulting to `Forgot to start/stop timer` per the Reason default
documented above. Same orphan-browser guard as steps 2 and 12 applies before opening the browser.

Prints one JSON array line, one object per input entry: `{...entry, ok: true}` on success or
`{...entry, ok: false, error}` on failure. Report any `ok:false` entry to the dev instead of
assuming the run fully succeeded.
