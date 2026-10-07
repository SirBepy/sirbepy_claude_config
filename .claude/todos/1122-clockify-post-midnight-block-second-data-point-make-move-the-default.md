<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=8, reconfirm-count=1, content-hash=d4617238 -->
<!-- duplicate-checked: done/1016 added the post-midnight placement QUESTION with one data point and
an explicit "replace with a default once a second run confirms" clause. This is that second data
point; no live todo covers it. -->
# clockify-reconciliator: post-midnight block has its second data point, make "move to same-day afternoon" the default

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-07

## Goal

Replace step 7's post-midnight placement question with a default: a block starting roughly
00:00-06:00 local moves into the same calendar day's afternoon, sized to its real minutes, placed in
a gap that doesn't overlap a same-project entry. No question asked. This follows the clause step 7
already carries: "if a second run confirms the dev always wants these moved, replace this question
with that default and record both data points here first."

## Context

- Data point 1 (2026-09-25, from done/1016): commit `ed9dc9c` at 02:03 Fri. The dev rejected the
  rendered 01:45-02:25 block and had it written as 13:30-14:15 the same day.
- Data point 2 (2026-10-07, zng-app session, Zirtue week of 2026-10-05): two chat sessions resumed
  ("continue") at Tue 2026-10-06 00:36-00:57. Asked where the ~20m should go, the dev picked "Tue
  afternoon" over "drop" and "keep real time". It was written as Tue 13:05-13:25. On 2026-10-06 the
  dev had also said in-session that he "shouldn't show I was working that late".
- Both picks went to the SAME day's afternoon, not the next working day.
- Bound unchanged: a 22:00-00:00 evening block still needs no move (done/1016's counter-example).

## Approach

Edit `C:\Users\tecno\.claude\skills\clockify-reconciliator\SKILL.md` step 7's last bullet (the
"A block starting between roughly 00:00 and 06:00 local is a placement decision" paragraph):

- Record both data points there first, as the clause requires.
- Change the rule to a default: move the block into that day's daytime gap nearest the start of the
  day's real work, keeping its real duration and 5-minute boundaries. The run reports the move
  ("00:36-00:57 activity moved to 13:05-13:25") in step 9's plan text. The dev can still override
  it at the apply gate.
- Remove the matching "resolve its placement as its own AskUserQuestion" sentence from step 9.

## Acceptance

- Step 7 lists both data points with dates and states the move-by-default rule.
- Step 9 no longer asks a separate post-midnight placement question.
- A 22:00-00:00 block is still explicitly out of scope for the move.
