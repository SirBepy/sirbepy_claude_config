<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no todo in this backlog mentions the week calendar, show_preview or hs_get_token caching -->
# 997 - clockify-reconciliator: script the week calendar and cache the HubStaff access token

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-23

## Goal

Two mechanical gaps in `skills/clockify-reconciliator/` that cost a full run tokens and a rule
violation on 2026-09-23 (zng-app session c24838e2, Zirtue week of 2026-09-21).

## Context

1. **The step 9a week calendar is hand-authored HTML every time.** The run pushed the
   `clockify-week` card four times (proposal v1, v2, v3, final), each a ~120-line document written
   by hand from the same block list, with pixel arithmetic (56px per hour, cropped gutter, break
   lanes) redone by eye each time. That is exactly the "hand-rolled measurement" pattern the
   skill's own diff mode was created to stop.
2. **Step 11's "re-fetch both sides live before reporting" cannot be honoured after the first
   token exchange.** `scripts/hs_get_token.ps1` prints the access token to stdout inside one
   PowerShell tool call; state does not persist across calls, the refresh token has already
   rotated, and `hubstaff.md` bans a second exchange (rate limit). The run fetched HubStaff
   activity once before the Clockify writes and had to report the comparison from that stale
   fetch, labelled as such, instead of the live re-fetch the rule requires.

## Approach

- Add `scripts/render_week_calendar.py` (or `.cjs`) that takes a JSON file of `{day, start, end,
  state, description, clockifyId?, breaks?}` blocks plus the target hours and emits the exact
  layout `SKILL.md` step 9a specifies (headline, target bar as legend, 46px gutter, 56px/hour
  cropped grid, four states with colour AND pattern, other-project lane, hover card with minutes).
  Update step 9a to call it and pass the output to `show_preview`.
- Make `hs_get_token.ps1` cache the access token (24h validity) in a mode-600 file next to the
  profile dir (e.g. `%LOCALAPPDATA%\claude-clockify\hubstaff-access-token.json` with an expiry),
  and have steps 11 and 12 read the cache first; only exchange when absent or expired. Document
  the cache path in `hubstaff.md`.

## Acceptance

- A run produces the calendar card from the script with no hand-written HTML in the transcript.
- Step 11 can fetch HubStaff activity twice in one run (pre-plan and post-apply) with a single
  refresh-token exchange; `hubstaff.md` names the cache and its expiry.

## Notes

- Both halves reproduced again 2026-09-25 (zng-app, Zirtue week Sep 21-25), third consecutive run.
  Calendar: three hand-authored pushes under the `clockify-week` slug (single-day proposal, full-week
  proposal, applied state), each ~250 lines, with the `56px/hour` origin arithmetic re-derived by hand
  every time because the crop moved (`13:00-20:00`, then `01:00-24:00`, then `10:00-24:00` once an
  overnight block was moved into the afternoon). No layout bug this time only because a throwaway node
  script computed every `top`/`height` before the HTML was written - which is precisely the script this
  todo asks to make permanent.
  Token cache: the HubStaff activities API returned **zero activities for all five days** of a week
  with 28h in Clockify. That is either a real gap or a wrong query, and telling the two apart needs a
  second fetch against a known-tracked earlier period. The access token existed only inside the one
  PowerShell call that minted it, `hubstaff.md` bans a second exchange, so the run could not
  distinguish them and had to report the emptiness unverified. Note that step 11 now runs far less
  often (`SKILL.md` step 10a, added the same day, gates every HubStaff step on the week reaching
  `weekly_target_hours`), but that does not remove the need for the cache: within a single gated run,
  step 11's pre/post re-fetch plus step 12 still want the same token more than once.
- Reproduced again 2026-09-24 (zng-app session, Zirtue window Sep 23-24): the hand-authored gutter
  and day-body were positioned from two different coordinate origins (gutter ticks measured from
  the grid top, day-body blocks measured from below a `day-header` whose height wasn't subtracted),
  so every block rendered shifted about one hour relative to its own hour labels. The dev caught it
  visually ("12-14 is actually inbetween 13-15") on the first push; it took a second full hand-written
  revision to fix. Concrete argument for `render_week_calendar.py` owning the coordinate math once
  instead of re-deriving gutter/body offsets by eye each run.
- 2026-10-02 (zng-app, Zirtue week of 2026-09-28): the token cache would have saved two extra exchanges in one gated run. The first exchange happened inside a PowerShell call whose inline `node -e` script died on a quoting error, so that access token was lost with the process, and the post-write verification needed a third exchange. All three succeeded with no rate_limit, but only by luck. The script-the-calendar half of this todo is already done (`scripts/render_week.cjs`); only the token cache is still open.
