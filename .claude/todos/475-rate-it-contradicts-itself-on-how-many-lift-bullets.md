<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /rate-it states two different caps for the How-to-raise block, 12 lines apart

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/rate-it` state one cap for the How-to-raise bullets instead of two conflicting ones.

## Context

Found 2026-08-22 while running `/heal-skill` end to end on `/rate-it` for todo 436.

`skills/rate-it/SKILL.md:107` (Output format, the section a session reads while composing the
block):

> Then a blank line and a `**How to raise the score:**` block: **2-4 bullets**, each a concrete
> change with the score it would unlock

`skills/rate-it/SKILL.md:114` (How-to-raise rules, 7 lines later):

> - **Cap at 3 bullets.** 2 strong beats 3 weak.

Four bullets is simultaneously allowed and over the cap. This is pattern **P6** in
`skills/heal-skill/references/confusion-patterns.md`: two of the skill's own rules holding
different standards for the same decision.

It has not been observed biting on the unmodified skill: across five recorded runs of eval fixture
5 the bullet counts were 3, 2, 3, and two runs used the no-lift hatch. A four-bullet response WAS
produced by a mutated copy during 422's regression probe, and fixture 5's "at most 3 suggested
improvements" expectation caught it, so the harness will catch this if it ever fires for real.

Filed rather than patched because `/heal-skill` diagnoses one cause per run and that run's evidenced
symptom was the ordering rule, not the cap. Two patches in one run means neither is attributable.

## Approach

1. Decide which number is right. `2-4` is the older wording; `Cap at 3` was added later with a
   rationale attached ("2 strong beats 3 weak"), so 3 is the likely intent.
2. Fix the loser at `skills/rate-it/SKILL.md:107` so the Output format section states the same cap,
   since that is the section actually read while the block is being written.
3. Do not add a third statement of the cap anywhere. One number, stated at the point of use.

## Acceptance

- `grep -n 'bullets' skills/rate-it/SKILL.md` shows exactly one cap, and the two sections agree.
- Eval fixture 5's "at most 3 suggested improvements" expectation still passes.

## Notes

Related, and NOT this todo: the ordering rule at `skills/rate-it/SKILL.md:113` was violated in 2 of
3 recorded runs that produced two or more scored bullets. That has its own diagnosis and patch from
the same `/heal-skill` run, awaiting the dev's approval.
