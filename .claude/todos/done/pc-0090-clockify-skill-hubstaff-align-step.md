<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=3d107f6f -->
# Add an opt-in "align HubStaff to Clockify" step to clockify-reconciliator

**Type:** skill-improvement

## Goal

Turn the ad-hoc HubStaff entry editing done by hand on 2026-07-26 into a documented, repeatable step of `/clockify-reconciliator`, so the next alignment does not require rediscovering the UI.

## Context

Step 11 of the skill compares HubStaff vs Clockify day boundaries and is explicitly report-only ("Do NOT auto-fix anything here"). That is the right default. But on 2026-07-26 Joe followed the report with "now we gotta make sure that thursday and friday hubstaff aligns with the new clockify", and the whole edit path had to be worked out live:

- The v2 API cannot mutate time; everything goes through the web UI.
- Headless Playwright is blocked by Cloudflare on login; headed + persistent profile works.
- Locators must be scoped to `.modal-content:visible` (hidden template copies exist).
- The Reason dropdown is required and client-visible.

Full recipe captured in [[reference-hubstaff-ui-time-edit]]. That took roughly a dozen probe iterations to pin down.

What actually got applied that day, as a worked example: Thu 23 edited 21:38-00:00 -> 21:10-22:20; Fri 24 edited 00:00-09:40 (a timer left running overnight) -> 13:00-15:00; Fri 24 added 22:30-23:15. All three with reason "Forgot to start/stop timer".

**Second worked example, 2026-07-30** (chrome-devtools MCP wasn't available/failed to launch this session - fell back to the same raw-Playwright recipe below, confirming it as the right default rather than depending on any MCP browser tool):

- Dev's ask this time added a new wrinkle: "when adding a brand new entry in hubstaff, round it to the 5s like we do in clockify, so it's obvious we add it later." Worth baking into 11b as a default: new/added entries should snap to 5-minute marks even when a raw tracked timestamp wouldn't (Clockify's own manually-logged entries were already all on 5-min marks, so this was just "reuse the Clockify entry's own times verbatim", not independent rounding logic).
- The initial step-11 report used a plain per-day min-start/max-end comparison and dismissed Tue/Wed as "false positive from a midnight-spanning entry" - that reasoning was **wrong**. A midnight-spanning entry can leave a genuinely uncovered gap on the far side of the boundary (here: Wed 00:00-00:40, a real 40-minute chunk with zero HubStaff activity, hidden because Wednesday's "day start" per Clockify looked like 00:00 for an unrelated boundary reason). Min/max boundary comparison alone is not sufficient - see Approach item 7 below.
- Separately found a real "HubStaff has MORE tracked time than Clockify" case (Tuesday, automatic tracker ran ~43min through a break window that Clockify's manual entries show as a gap). Fixed via Actions -> **Split time entry** -> **DELETE TIME** tab, setting a FROM/TO sub-range inside the tracked block and deleting just that slice. This is a different remediation than Add/Edit and belongs in the same step 11b as a third case (see Approach item 8).
- Only caught the Wed gap because the dev pushed back on a "matches perfectly" claim that was itself compromised by a stale local scratch file (see [[feedback_verify_live_not_cached]]) - re-verify with a fresh live fetch before ever reporting full alignment, don't trust an intermediate file written earlier in the same session without checking it actually landed correctly.

## Approach

Add a step 11b to `~/.claude/skills/clockify-reconciliator/SKILL.md` (hardlinked - verify both copies after editing), gated behind explicit dev opt-in, never automatic:

1. Only offer it when step 11 flagged days outside the 10-minute tolerance.
2. Present the proposed per-day edits as a table (current HubStaff window -> target Clockify window) and require `AskUserQuestion` approval before any mutation, matching step 9's discipline.
3. Point at [[reference-hubstaff-ui-time-edit]] for the mechanics rather than restating the selectors, so there is one source of truth.
4. Prefer **Edit time entry** over delete-then-recreate; use **Add time** only when Clockify has more blocks that day than HubStaff.
5. Default the Reason to "Forgot to start/stop timer" but surface it in the approval table, since it is client-visible.
6. Verify after each mutation via the API rather than trusting the UI, and remember the single-exchange/rate-limit rule.
7. **Fix the underlying comparison, not just the fixing:** step 11's min-start/max-end-per-day check is not sufficient on its own - it misses internal gaps and misattributes midnight-spanning entries (2026-07-30 finding, see Context). Add a per-entry completeness pass: for every Clockify entry (including the halves of one that spans midnight), confirm HubStaff has *some* tracked/manual coverage overlapping its window, not just that the day's overall boundaries look close.
8. New entries added to HubStaff should reuse the source Clockify entry's exact timestamps (already 5-min-aligned in practice) rather than re-deriving/rounding independently - confirmed dev preference 2026-07-30.
9. Add a fourth remediation case beyond "Add" and "Edit": **trim** - when HubStaff has *more* tracked time than Clockify (automatic tracker ran through an unlogged break), use Actions -> Split time entry -> DELETE TIME with a FROM/TO sub-range, not a full Edit. Surface this distinctly in the approval table ("HubStaff has excess, not a gap") since it's the opposite direction from the other two cases.
10. Before presenting ANY "aligned"/"matches" conclusion to the dev, re-fetch both sides live in the same pass - never reuse a JSON scratch file written earlier without confirming its mtime is from this run (see [[feedback_verify_live_not_cached]]).

Rejected: doing this via the API. There is no v2 endpoint that mutates tracked time (`/time_entries` 404s).

## Acceptance

- A dev asking to align HubStaff after a reconciliator run gets a proposed-edit table and an approval prompt, not improvised selector hunting.
- Step 11 stays report-only; 11b never runs without explicit approval.
- The skill does not duplicate the selector recipe that lives in the memory file.
- Step 11's comparison catches internal/midnight-boundary gaps, not just whole-day boundary mismatches (2026-07-30 regression: a real 40-min gap was initially missed and only caught because the dev asked to double-check).
- 11b's approval table distinguishes three cases (add missing / edit boundary / trim excess), not just two.

## Notes

Consider whether this belongs in `/clockify-reconciliator` at all versus a separate `/hubstaff-align` skill. Argument for keeping it here: it only ever runs off the back of step 11's comparison and shares the auth/profile setup. Decide before implementing.
- completed, commit 8d83c75
