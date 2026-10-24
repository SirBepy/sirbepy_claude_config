<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped backlog for loop-todos + park/open questions/Phase 0; none covers end-of-loop asking -->
# /loop-todos parks questions for "the next invocation" instead of asking them before it stops

**Type:** skill-improvement
**Origin:** dev

## Goal

When a `/loop-todos` run stops, every question it parked during its cycles has already been asked
in one card, so Joe never finds open questions left behind after a loop he started to clear them.

## Context

Joe, 2026-10-24, after a `/loop-todos 4 --resumed` run in claude_usage_in_taskbar ended with three
todos (#1291, #666, #1316) carrying fresh `## Open questions` blocks "for the next Phase 0": "bruh,
i fucking asked another ai to ask me all questions that are left... defuq".

`skills/loop-todos/SKILL.md`'s Precedence section says "Questions Step 8 parks DURING the loop
belong to the NEXT `/loop-todos` invocation's Phase 0. They are never asked mid-loop." That rule
is what the run followed. Not asking mid-loop is right (it keeps cycles from stalling); deferring
to a future invocation is the part Joe rejected. The stop condition "AUTO queue empty" fires
exactly when only dev-input questions remain, which is the moment to ask them.

## Approach

In `skills/loop-todos/SKILL.md`:

- Add a phase between Phase 4.5 and Phase 5 ("Closing question round"): run Phase 0's steps 1, 3,
  4 and 5 again over every `## Open questions` block written during this loop (and any that were
  there already), one `ask_user_question` card, same standing options, same write-back. If the
  answers unblock todos and the cycle cap is not reached, start another cycle instead of stopping.
- Rewrite the Precedence line to: parked questions are never asked mid-cycle, they are asked in the
  closing round before the loop ends.
- Phase 5's report lists what was answered in the closing round, not "parked for next time".

## Acceptance

- SKILL.md has no remaining "NEXT /loop-todos invocation" wording for parked questions.
- A loop that stops on "AUTO queue empty" with parked questions asks them before its final report.

## Notes

- Added Phase 3.5 'Closing question round' (Phase 0 steps 1/3/4/5 over every Open questions block, one card, re-enters a cycle when answers unblock work and the cap and tree allow). Placed before Phase 4.5 rather than after it, so the per-commit review still runs once after the real last cycle. Precedence and Phase 5 no longer defer parked questions to the next invocation; grep for that wording is empty.
