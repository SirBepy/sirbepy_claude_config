<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 486 added the scope question itself, 905/1008 cover narrow-window cards, 1123 covers the show_preview transport; none cover the scope question arriving with no card to look at -->
# clockify-reconciliator: the step 3a target-scope question arrives before any preview card, and the dev asks to see the card first

**Type:** skill-improvement
**Origin:** ai

## Goal

When a run asks the step 3a target-scope question, the dev can already see a draft week card,
so they answer with the numbers in front of them.

## Context

`skills/clockify-reconciliator/SKILL.md` step 3a says the stated-target scope must be confirmed
via AskUserQuestion "before building anything toward it ... before any proposal table exists".
Step 9a's card is only built later, at step 9.

2026-10-15, revaire-mobile, week of 2026-10-12, Reconstruction mode with a stated 24h target:
the run asked the scope question (existing-inclusive or not, Mon-Thu vs Friday reserve) with only
a prose estimate ("about 20h"). The dev answered the card with "i dont see the /preview ...",
not with an option. The run then had to build and push a draft card, and the dev gave the real
answer ("i wont be working on friday, so i should have 24 by now") only after seeing it. That
cost one extra question round-trip.

## Approach

In step 3a, before asking the scope question, render a draft `clockify-week` card through
`render_week.cjs`. Use existing entries plus the evidence-backed blocks before any target fill,
and leave `--target-hours` off so the card makes no claim about the target. Then ask the scope
question with the card visible.

This keeps the step 3a rule's intent: no target-driven blocks get built before scope is
confirmed. The draft shows only evidence-backed time.

Rejected: dropping the scope question. It exists because of the 2026-08-22 overshoot (see
step 3a), and this run needed it too, because Friday's status changed the answer.

## Acceptance

- A Reconstruction run with a stated target pushes a draft card before the scope question.
- The draft card carries no target ring (no `--target-hours`) until scope is confirmed.
- Step 3a's "never build toward the target before scope is confirmed" rule still holds.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1) in the clockify-reconciliator batch commit.
