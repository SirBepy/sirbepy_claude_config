---
name: clockify-reconciliator
description: Adds descriptions to description-less Clockify entries for a configured project, splitting large blocks into 1-3h chunks using git commits from configured repos.
disable-model-invocation: true
argument-hint: <project-name> [lookback]
---

# /clockify-reconciliator

> Fill empty Clockify descriptions from git commits.

## Inputs

- `<project-name>` (optional if cwd resolves to exactly one config, see Step 1): matches `~/.claude/skills/clockify-reconciliator/projects/<project-name>.md`.
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

If `<project-name>` was omitted: grep the `repos:` lists in every config under
`~/.claude/skills/clockify-reconciliator/projects/*.md` for the current cwd (or a parent of it).
Exactly one match: use it silently, state which config was resolved and why in the run's first
output line. Zero or multiple matches: ask via AskUserQuestion.

Read the named file. Abort with clear error listing missing required fields.

**Resolve the Clockify API key here, before any API call:** use the env var named by `api_key_env` if the config sets it, else `CLOCKIFY_API_KEY`. Every Clockify request in steps 4 and 9 sends that value as the `X-Api-Key` header. Getting this wrong does not error loudly - the default key against another account's workspace returns 403 or an empty entry list, which looks exactly like "nothing to reconcile", so state which var you resolved in the run's first output line. If the resolved var is unset, abort and name it.

### 2. HubStaff screenshot preflight (skip if `hubstaff_org_id` not set)

If `hubstaff_org_id` is set, read `skills/clockify-reconciliator/hubstaff.md` now and follow its "Step 2" section before any reconciliation work, so the dev can fix auth without waiting through the full run.

### 3. Resolve window

**The dev's timezone is `Europe/Zagreb`.** It is stated here, at skill level, not per project - the dev is in one place, so a copy in every `projects/*.md` would only be a second thing to keep in sync. Every "dev's timezone" and "local" below means that zone. Record the zone NAME and let the runtime resolve the offset: Croatia is UTC+1 in winter and UTC+2 in summer, so any hardcoded numeric offset is wrong half the year.

Clockify's API stores and returns entry times in UTC. Convert explicitly in BOTH directions - `Europe/Zagreb` local to UTC when writing an entry in step 9, UTC to `Europe/Zagreb` when reading one in step 4 - rather than deriving the offset from whatever entries already exist. That derivation (diff a known local time against its stored UTC timestamp) is a legitimate FALLBACK, and it worked on 2026-08-16, but it is unavailable on exactly the day it matters most: a day whose first entry is the one being written has nothing to diff against. The failure mode is silent - right duration, wrong hour, which looks normal in a weekly total.

If `[lookback]` given, parse it. Else: Monday 00:00 of current week to now, in dev's timezone.

For a single-day lookback (`today`, `yesterday`, or an explicit single `YYYY-MM-DD`), the window is always a full local calendar day, true midnight-to-midnight: `<day> 00:00:00` to `<day+1> 00:00:00`, dev's timezone. `today` = the current calendar date; `yesterday` = current calendar date minus 1 calendar day. Compute the calendar date first, then take that date's midnight-to-midnight span - never derive the boundary as "now minus 24h", and never use a rounded/approximate cutoff (e.g. `22:00`) in place of true midnight. This window feeds both the Clockify entry fetch (step 4) and the git-log bounds (step 6). See `~/.claude/projects/c--Users-tecno-Desktop-Projects-zng-app/memory/feedback_verify_date_calculations.md` for the 2026-07-28 incident this rule fixes.

### 3a. Resolve mode

- **Reconciliation** (default): fill empty descriptions on existing entries, surface commit-backed
  gaps for approval (step 6a). No override needed - this is always safe to run.
- **Reconstruction**: the window has zero or sparse existing entries and the dev's ask implies
  building the period from scratch (e.g. "I haven't logged anything this week", "rebuild my week").
  Confirm scope once via AskUserQuestion, "This session only" as the only offered option, before
  sourcing anything beyond commits, then read `skills/clockify-reconciliator/modes.md`'s
  "Reconstruction mode" section for the full procedure.
- **Audit**: the dev explicitly asks to check/fix a period that already has entries (e.g. "check the
  whole month", "audit July"). Requires one AskUserQuestion confirming the override of the "never
  touch existing / never create in gaps" defaults, scoped to this session only, then read
  `skills/clockify-reconciliator/modes.md`'s "Audit mode" section for the checklist.

Reconstruction and Audit are never inferred silently from window contents alone - the trigger is the
dev's own phrasing, confirmed once via AskUserQuestion before any of their extra sourcing/checklist
work begins. A plain Reconciliation run never needs to read `modes.md`.

### 4. Fetch Clockify entries

Authenticate with the key resolved in step 1 (`api_key_env` or `CLOCKIFY_API_KEY`), not with `CLOCKIFY_API_KEY` by reflex.

Call `GET /workspaces/{ws}/user/{user}/time-entries?start=...&end=...&page-size=200` — do NOT pass `hydrated=true`, it bloats each entry with full user/project objects. Only fields needed: `id`, `description`, `timeInterval`, `projectId`, `billable`, `tagIds`. Bucket:

- In-project (matches `clockify_project_id`)
- Other-project (for the warning)

**Integrity check:** confirm every returned `timeInterval.start` actually falls inside the requested
window. A first fetch after a date-window change can return an unrelated past window's entries (stale
response, HTTP 200). If any entry is outside the window, re-fetch once before trusting the result -
never build a plan, or report "nothing to reconcile", off a stale response.

### 4a. Memory check

Before identifying targets, read `feedback_clockify_*.md` memory files for the resolved project and
apply them: default every new/edited entry to `billable: false` (Cinnamon convention, not the actual
billing signal); check same-day entries for time overlap before creating anything, shrink/shift the
new block instead of double-counting; never add net-new hours to a day that already has entries except
the two confirmed cases in "Rules" below.

### 5. Identify targets

Target = in-project entry with empty or whitespace-only description.

**Day has some entries but real work is unlogged** (distinct from an empty-description target and
from a zero-commit day): if the dev recalls unlogged work on a day that already has entries, branch:
- A commit/tracker trail exists for the extra time: propose it like any other target, explicitly call
  out the day-total change in the plan (step 9) before applying - matches the net-new-hours exception
  in Rules.
- No trail exists (pure recollection, e.g. manual UI testing): say so plainly and ask the dev for a
  number rather than inventing one. Don't silently fall through to "nothing found" either.

### 6. Read commits

For each repo in config: `git -C <repo> log --author="<user_id or name>" --since=... --until=... --pretty=format:...`, using the window resolved in step 3. Capture sha, ISO timestamp, subject, body, branch (best-effort via `git branch --contains`).

Then run one more pass per repo covering the first 4 hours after the window's END: `--since="<end>" --until="<end> + 4h"`. For a single-day lookback that is `<day+1> 00:00:00` to `<day+1> 04:00:00`; for a multi-day range it is the same 4 hours past the range's final midnight. Flag hits as "late-night spillover from <last day in window>" and split them across the boundary by each commit's real wall-clock minutes on its own calendar day. Never drop them, never fold the whole session onto one side.

### 6a. Gap detection (mandatory in every mode, including plain Reconciliation)

Diff the commits just read (whole window, not just around existing targets) against the entries that
exist. Any day or multi-hour block with commits and no covering entry is a finding - add it to the
step 9 proposal table next to the empty-description targets. A window containing a fully unlogged
workday can never be reported as "nothing to reconcile" just because no empty-description targets
exist.

**Gap-fill sizing:** default to the full first-commit-to-last-commit window for that day, chunked into
1-3h blocks, not just the isolated minutes immediately around each commit cluster - the latter
undershoots real gaps between clusters. If the day has zero existing entries, don't ask the dev for
start/end times; infer them from commit-gap clustering the same way (first chunk starts ~2h before the
first commit cluster, last chunk ends shortly after the last commit) and present the plan for the
normal step 9 approval.

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

If gated in, read `skills/clockify-reconciliator/hubstaff.md` and follow its "Step 11" section. If the
dev then asks to update/sync HubStaff (not just compare), follow its "HubStaff update mode" section
instead of improvising scope or entry-creation mechanics.

### 12. HubStaff weekly screenshot (skip if `hubstaff_org_id` not set or preflight marked auth as failed)

If gated in, read `skills/clockify-reconciliator/hubstaff.md` and follow its "Step 12" section.

### 13. Report

- Mode used (Reconciliation / Reconstruction / Audit)
- Entries written (count + per-day summary)
- Gap-detection findings (step 6a): unlogged days/blocks surfaced, applied or still pending approval
- HubStaff comparison results (step 11), or "HubStaff comparison skipped - hubstaff_org_id not configured" if absent
- HubStaff weekly screenshot path(s) (step 12), or skipped reason (auth failed preflight / org not configured)
- "Needs manual" targets with time + reason
- Other-project warning list

## Rules

- Never touch an entry that already has a non-empty description, outside Audit mode's explicit,
  session-scoped override.
- Never invent hours not backed by a real commit/PR or an explicitly named real activity - this is the
  actual ban, not "never look at unlogged days" (step 6a surfaces commit-backed gaps for approval in
  every mode; Reconstruction and Audit extend what counts as backing, per their own sections).
- Every new/edited entry defaults `billable: false` (step 4a) and must not overlap another same-day
  entry - shift/shrink the new block instead of double-counting.
- Never add net-new hours to a day that already has entries, except: (a) a concrete commit trail backs
  the extra time and the day-total change is called out explicitly before applying, or (b) filling
  toward a weekly target the dev explicitly stated, sized from real evidence, on a day with ZERO
  existing entries only. A stated weekly target is a ceiling to fill toward, never a license to invent
  hours beyond real evidence.
- Max 80 chars per description.
- Ticket suffix only if a matched commit carries one. One ticket per description, most relevant. Number appears once, in parens, at the end - never repeated as a leading prefix too.
- No em dashes. Commas or hyphens.
- Every entry's start and end time, written or created, lands on a 5-minute mark with :00 seconds. Never a raw commit-derived minute (18:56, 22:12, etc).
