<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=7, reconfirm-count=2, content-hash=0ce264b2 -->
<!-- duplicate-checked -->
# Clockify's time-entries fetch silently excludes entries whose `end` lands exactly on the query's `end` param

**Type:** skill-improvement
**Origin:** ai

## Goal

Document (and route around) a Clockify API quirk in `skills/clockify-reconciliator/SKILL.md`
step 4's Integrity check: `GET .../time-entries?start=...&end=...` treats `end` as exclusive, so
an entry whose `timeInterval.end` equals the query's `end` param is silently dropped from the
response, with a normal 200 and no error.

## Context

2026-08-27 zng-app session, `/clockify-reconciliator` for "today", then a follow-up week audit.

Hit twice in the same session:
1. After creating 6 entries for the day (last one 21:00-22:00Z, window end also 22:00Z), a
   verification re-fetch using that same window returned only 5 of the 6. Fetching the 6th
   entry directly by id proved it existed exactly as written - the list endpoint just excluded it.
2. Recreated later in isolation to confirm it wasn't a one-off: same window-boundary shape,
   same silent exclusion.

Worked around in the moment by widening the fetch window's `end` param days past any real data
(e.g. querying through end-of-week instead of "now"), which sidesteps the exclusion since no real
entry then sits exactly on the boundary. This works but is a workaround, not a documented rule -
next session hits the same false "it's missing" scare from scratch.

The skill's own step 4 Integrity check already warns about a *different* boundary failure mode
(stale response after a date-window change, entries outside the window) but says nothing about
entries *silently missing* despite being inside the window and correctly written. A "nothing to
reconcile" or "entry N is missing" conclusion drawn from a fetch whose window end lines up with a
real entry's end is currently indistinguishable from a real problem.

## Approach

Add a bullet to SKILL.md step 4 (Integrity check), near the existing stale-response guidance:

- State the exclusive-`end` behavior explicitly.
- Recommend always fetching with `end` padded past the window actually needed (e.g. next
  midnight, or the following day) rather than the exact boundary time, whenever the fetch is
  being used to *verify* a specific entry rather than just to read a bounded window.
- If a verification fetch is missing an entry that was just created/edited (id known), fetch that
  id directly (`GET .../time-entries/{id}`) before concluding anything is wrong.

## Acceptance

- SKILL.md step 4 states the exclusive-`end` quirk and the pad-past-the-boundary mitigation.
- A future session verifying "did entry X write correctly" via a window fetch that happens to end
  exactly on X's end time no longer misreports X as missing.

## Notes

Not reproduced against other Clockify endpoints (only the time-entries list fetch was exercised
this session) - scope the fix to that endpoint unless a future session finds the same behavior
elsewhere.
