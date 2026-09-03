<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: guard hits (503 token helper, 830 audit gap-detection, 100 playwright-mcp, 232 token rotation, 396 hubstaff config template) only share generic vocabulary (clockify/reconciliator/single/week/weekly) - none touch step 9a's visual or the weekly-target-bar framing -->
# clockify-reconciliator week-calendar visual claims a weekly-remaining figure on a single-day run

**Type:** skill-improvement
**Origin:** ai

## Goal

Step 9a's headline/target-bar (`weekly_target_hours` framing) must never present a
"remaining this week" number when the run only fetched one day's data.

## Context

Found 2026-09-03 on zng-app, `[lookback]=today`. The skill fetched only today's Clockify entries
(as designed for a single-day lookback), summed them to 10h20m, then rendered the headline as
"10h 20m ... of 30h weekly target" with a pill reading "19h 40m to go this week". That number is
only correct if zero hours were logged on every other day of the week, which was never checked -
the run had no data for Mon/Tue/Wed/Fri/Sat/Sun at all. Joe caught it immediately: "19h 40m to go
this week is inaccurate, because youre not looking at the entire week."

Fix applied ad hoc this session (not written back to SKILL.md): dropped the weekly-remaining pill
and target bar entirely for the single-day run, replaced with a plain "counted today" headline and
a same-day state-breakdown bar (old/new/meeting proportions of today's total only, no target
denominator).

This is distinct from `done/486-clockify-reconciliator-weekly-target-scope-ambiguous.md` (already
fixed) - that todo covers confirming what a dev-STATED target covers before sizing work toward it.
This bug is different: no target was stated in this run at all, `weekly_target_hours` is just the
static config default, and the violation is purely visual/honesty - step 9a computing a
week-relative "remaining" claim from a fetch that never covered the week.

## Approach

In `skills/clockify-reconciliator/SKILL.md` step 9a: gate the target-bar/weekly-remaining framing
on whether the resolved window (step 3) actually spans the full current Mon-Sun week. For any
lookback that resolves to less than a full week (`today`, `yesterday`, an explicit single-day
range, or a partial-week `past-N-days` that doesn't align to Monday), render only a same-window
total and a same-window state breakdown, no weekly target/remaining figure. Keep the weekly
target bar only when the window provably covers the whole week the target refers to.

## Acceptance

- A single-day (or any partial-week) run never shows a "to go this week" or "of Nh weekly target"
  claim computed from less than a full week's fetch.
- A full-week run keeps the existing target-bar behavior unchanged.

## Notes

Related: [[486-clockify-reconciliator-weekly-target-scope-ambiguous]] (stated-target scope
confirmation, already fixed, different bug).
