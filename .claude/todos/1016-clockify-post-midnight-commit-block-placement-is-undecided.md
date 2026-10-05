<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped active + done/ for "overnight", "small hours", "small-hours",
"late-night", "02:03" - the only hits are done/485 (branch scoping), done/815 (fetch staleness),
done/90 (hubstaff align) and done/91 (midnight-to-midnight WINDOW resolution). None covers where a
post-midnight commit cluster's BLOCK should be placed once the window is already resolved. -->
# clockify-reconciliator: a post-midnight commit cluster's block placement is undecided

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-25

## Goal

`SKILL.md` step 6 and `modes.md`'s clustering defaults say where a post-midnight commit cluster
belongs on the CALENDAR (its own day, split by real wall-clock minutes), but nothing says whether
its block should be rendered at its real small-hours time or moved into that day's working hours.
The one run that produced such a block had it rejected on sight, so the current mechanical answer is
the wrong default at least some of the time.

## Context

2026-09-25, zng-app, `/clockify-reconciliator zirtue yesterday` (window later widened to the full
Mon 2026-09-21 to Fri 2026-09-25 week at the dev's request).

Commit `ed9dc9c` ("55999: Trim the landing-page helper dartdocs to their contract") landed
`2026-09-25 02:03:22 +02:00`. Step 6's late-night-spillover rule correctly put it on Friday's own
calendar day rather than folding it onto Thursday (7h after Thursday's last commit, so well past the
3h session break). `modes.md`'s +/-20min pad then produced a block at **01:45-02:25**.

The dev rejected it outright: *"lets not add the friday at 1:45 to 2:25AM, lets rather just put that
in the PM, so like 1:30PM till 14:15PM"*. It was written as `13:30-14:15` (45 min) instead, and the
run's week calendar re-cropped from `01:00-24:00` to `10:00-24:00` as a result, which also removed a
7.5h dead band from the visual.

**One data point, and it has a real counter-example bounding it.** The same week's Monday entry is
`22:00-00:00`, a pre-existing entry the dev wrote himself and left untouched through this run. So the
preference is not "never log outside business hours" - a 22:00 start is fine. It is specifically
about a block whose start falls PAST midnight. Do not generalise this into a blanket
working-hours-only rule.

## Approach

In `SKILL.md` step 7 (build proposals), add: a proposed block whose start falls between roughly
`00:00` and `06:00` local is a placement DECISION, not a mechanical one. Surface it in step 9's
`AskUserQuestion` as its own option pair rather than silently rendering it at its real hour:

- keep it at the real small-hours time, or
- move it into that day's daytime hours (the dev names the slot, as he did here).

Reasons it cannot be defaulted silently either way:

- The skill has no way to know whether the true hour matters to whoever reads this Clockify project.
- Keeping it also forces the step 9a calendar crop down to `01:00`, which adds a multi-hour empty
  band to every column in the week view - a visible cost paid for one 40-minute block.
- Moving it silently would be inventing a time the evidence does not support, which the Rules
  section bans.

Whatever the dev picks, the commit is still counted on its own calendar day (step 6's split rule is
unchanged) and both boundaries still land on a 5-minute mark.

## Acceptance

- A run whose plan contains a block starting before ~06:00 asks about its placement in step 9 rather
  than rendering it at the real hour and waiting to be corrected.
- The Monday `22:00-00:00` case still passes through untouched with no question asked, so this does
  not turn into a prompt on every evening block.
- If a second run confirms the dev always wants these moved into the afternoon, replace the question
  with that default and record the two data points here before doing it.
