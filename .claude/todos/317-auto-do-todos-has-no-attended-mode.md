<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=7, reconfirm-count=1, content-hash=59442bb4 -->
# /auto-do-todos has no path for a dev who is present and answering

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/auto-do-todos` an explicit attended mode, so a run where Joe is sitting there answering does
not have to violate the skill's own contract to work well.

## Context

The 2026-08-13 run broke two of the skill's stated rules, and breaking them was the right call both
times, which is the tell that the contract is wrong rather than the run.

**Rule 1, one question round.** `skills/auto-do-todos/SKILL.md` Step 5 is titled "The one question
round" and states "Steps 6 and 7 never ask, no matter what they find." The run asked three times:
the Step 5 round, a second round carrying explanations Joe explicitly requested ("can you explain
this issue better again?", "explain the issue a bit better, and /rate-it each solution"), and a third
about sequencing 11, 30 and 63. Joe had opened the run with "pls feel free to actually ask
questions", and every extra round produced a decision that unblocked real work.

**Rule 2, run the nested skills.** The Order of operations says step 2 is `/cleanup-todos` and step 3
is `/batch-todos`, both unattended. Neither ran. The run went straight to Step 4 triage because a
single triage agent covered what both would have produced, on a 20-item backlog, for one dispatch
instead of two skill invocations.

The skill is written for `/autopilot`'s premise: dev is AFK, interruption is the expensive thing. The
Precedence section says so outright. It has no notion of the opposite case, where the dev is present,
answering within seconds, and a refused question costs more than an asked one.

## Approach

Add an attended mode. The trigger should be evidence, not a flag Joe has to remember: the invoking
prompt inviting questions ("feel free to ask", "ask me anything") is the signal the 2026-08-13 run
actually had, and it is already in the args.

What changes in attended mode:

- Step 5's one-round cap lifts. Steps 6 and 7 may ask, but only for a fork that genuinely blocks
  the todo in hand, never for something Step 8 could park.
- A question Joe answers with a request for explanation is not a failed round, it is a normal turn.
  Budget for it rather than treating the round as spent.

Also decide, separately, whether steps 2 and 3 should be conditional on backlog size. Two nested
skill invocations to dedupe 20 items is worse than one triage agent that does both, and the run
proved it; but on a 120-item backlog the nested skills probably earn their keep. Name the threshold
rather than leaving it to judgement, or the next run will skip them too and rationalise it after.

## Acceptance

- The skill states when a run is attended and what changes, in its own words, so a run does not have
  to decide it silently.
- Steps 2 and 3 carry an explicit condition for when they run, not an unconditional "always".
- A future run that asks three times in attended mode is following the skill, not deviating from it.

## Notes

- Filed by `/close` Phase 1 on 2026-08-13, from the run's own rule violations.
- Do not "fix" this by making the run ask less. The extra rounds were what made the run useful; the
  contract is what was wrong.
