<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: nothing in the backlog or done/ covers the question-round TRIGGER; todo 410 and 886 are about message and question-card mechanics, not about when a run consults the dev. -->
# The question-round trigger scales backwards with backlog size

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether `/auto-do-todos` Step 5's question-round trigger should stay purely
"is the AUTO queue empty", given that it makes the largest runs the least likely to consult the
dev.

## Context

Noticed 2026-09-04 during the `/mega-todos` run over `~/.claude`. Not a bug - the run followed the
contract exactly - but the contract has a property worth looking at deliberately.

Step 5 fires only when the AUTO queue is **empty**, or a todo already carries an
`## Open questions` block, or the run is in cleanout mode. Its stated rationale is good: "a run that
has real work to do never interrupts the dev."

The consequence, at scale: a 133-todo backlog produced a large AUTO queue, so the round never
fired, and the run dispatched **69 builders across two waves with zero dev input**, parking 16
dev-only forks for the next run. A 5-todo backlog with 4 DEV items would have asked immediately.
So the probability of the dev being consulted falls as the run gets bigger, which is the opposite
of how blast radius scales.

Two of the parked forks were things only the dev can do at all (455 needs an explicit `git push`,
836 is misfiled into the wrong repo's backlog), and three more were architecture calls with real
blast radius (410, 502, 467). None of them blocked any AUTO work, so parking them cost nothing this
time - which is the honest counter-argument, and it may well be the right answer.

The question is genuinely open, and the global `CLAUDE.md` rule ("front-load all questions before
starting work, trivial or not") sits on the other side of it, superseded for unattended runs by
`/auto-do-todos`'s own Precedence section.

## Approach

Options, to be decided rather than assumed:

1. **Leave it exactly as-is.** Defensible: the forks did not block anything, and the next run opens
   with them. Cost is latency on the dev's own decisions, not on the work.
2. **Add a size trigger** - fire the round when the run will dispatch more than N builders, or when
   more than N DEV forks were found, regardless of whether AUTO work remains. The uncapped
   `mcp__cc_conductor__ask_user_question` makes a 16-question round one card, so the cost is one
   interruption, not sixteen.
3. **Fire only for the subset that gates other work** - a DEV fork whose answer changes an AUTO
   todo in the same lane. This run had a few (502 sits on the same file region as 498/849/860/862).
4. **Ask at the END** rather than the start, once the waves are done and the dev is being handed a
   summary anyway. Costs nothing mid-run and still gets answers the same day.

Option 4 is worth serious weight: it preserves "never interrupt a run that has work to do" while
removing the whole-run latency, and the summary turn is already an interruption.

## Acceptance

- A decision is recorded in `skills/auto-do-todos/SKILL.md` Step 5, with its reason, whichever way
  it goes - including "stay as-is", which is a valid outcome and should be written down so this is
  not re-litigated.
- If a new trigger is added, `/mega-todos` inherits it by reference rather than restating it, per
  the existing "triage logic lives in exactly one place" rule.

## Notes

- Filed by /close on 2026-09-04 from the `/mega-todos` run's own retrospective. Origin is `ai`: the
  dev did not raise this, the run noticed it about itself.
- Fixed in 4ab5a5b: the question-round trigger decision is now recorded with reasoning in auto-do-todos. Real evidence from this run - 67 todos, 20 carrying Open questions - fed the call.
