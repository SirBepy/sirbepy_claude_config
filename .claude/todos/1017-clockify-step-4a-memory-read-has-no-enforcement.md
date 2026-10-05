<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=fa99b9c0 -->
<!-- duplicate-checked: grepped active + done/ for "4a", "memory check", "feedback_clockify" -
done/82-clockify-reconciliator-memory-check-and-unlogged-day.md is what CREATED step 4a (it added the
memory-check step at all). This is the follow-on: the step exists and was skipped with nothing
catching it. No active or done todo covers enforcing it. -->
# clockify-reconciliator step 4a says "read the feedback_clockify_* memory files" and nothing catches a run that doesn't

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-25

## Goal

Step 4a's memory read is a prose instruction with no artifact proving it happened, so a run can build
and apply a whole plan with the project's own Clockify conventions never consulted. Make the read
visible in the run's output, the way step 1 already makes the resolved API-key var visible.

## Context

2026-09-25, zng-app, `/clockify-reconciliator zirtue`, 8 entries written for the Sep 21-25 Zirtue week.
Step 4a reads:

> Before identifying targets, read `feedback_clockify_*.md` memory files for the resolved project and
> apply them

**Zero of the seven files were opened.** The run worked off the recalled `MEMORY.md` index line
instead, which is one line of hooks, not the rules. The seven that exist today:
`feedback_clockify_check_uncommitted_repos`, `feedback_clockify_filter_every_fetch_by_project`,
`feedback_clockify_infer_project_from_cwd`, `feedback_clockify_meal_breaks_and_unattended_work_next_day`,
`feedback_clockify_no_billable_flag_no_overlap`, `feedback_clockify_no_extra_hours`,
`reference_clockify_stale_first_fetch`.

The two rules step 4a names inline (`billable: false`, per-project overlap scope) were followed anyway,
because step 4a restates them in its own body. The rules that live ONLY in the memory files were not:
`feedback_clockify_meal_breaks_and_unattended_work_next_day` requires a lunch gap at 11:30-12:00 and a
dinner gap at 18:30-19:30 cut out of contiguous commit windows, and it was never applied.

**Consequence this run was nil, by luck, not by process.** Thursday's blocks started 13:30 (past the
lunch window) and the dev's own stated standup already occupied 18:05-19:00 (covering the dinner
window); the Tue/Wed gap-fills and Friday's blocks fell outside both windows. A day proposed as
10:00-20:00 would have shipped with neither gap cut, which is the exact thing the dev asked for on
2026-09-23.

The same run later re-derived the post-midnight placement question from scratch and got corrected by
the dev, when point 2 of that same unread memory file already covered the principle ("never assume a
commit at 21:20 means he was at the keyboard at 21:20"). So the skipped read had a real cost, just not
in the written entries.

## Approach

In `SKILL.md` step 4a, make the read produce evidence rather than asking for good behaviour:

- Glob the memory dir for `feedback_clockify_*.md` and `reference_clockify_*.md` and read every hit -
  no filename list hardcoded in SKILL.md, since the set grows.
- Print one line naming the files actually read, in the run's output, before the step 9 plan. Same
  pattern as step 1's "state which var you resolved" line, which exists for the same reason: a silent
  skip and a silent success look identical.
- State explicitly that the recalled `MEMORY.md` index line is NOT the memory - it is a pointer, and
  reading it does not satisfy this step.
- Fold any rule from those files that constrains block layout (meal gaps today) into the step 7 /
  `modes.md` clustering defaults as a named checklist item, so the proposal builder consults it at the
  point it lays out blocks rather than relying on step 4a having been read 3 steps earlier.

## Acceptance

- A run's output names the clockify memory files it read, so a skip is visible in the transcript.
- A proposed day spanning 11:30 or 18:30 has the meal gaps cut without the dev asking, on a run where
  nobody re-read the memory by hand.
