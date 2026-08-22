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

## Second fix in this same section, folded in 2026-08-22: the ordering rule

Same file, same section, one more one-line edit, so it lives here rather than in a second todo.

`/heal-skill`'s live run diagnosed this and produced the patch; it is **awaiting the dev's
approval** and was deliberately not applied. Full record in `skills/rate-it/heal-log.md`.

**Symptom:** the How-to-raise bullets are not ordered by unlocked score. Observed as
`6/10, 5/10, 6/10` and `6/10, 5/10` in 2 of the 3 recorded eval runs that produced two or more
scored bullets (5 runs total; 2 used the no-lift hatch and produced none).

**Cause, pattern P1** (the rule depends on being remembered): `skills/rate-it/SKILL.md:113` states
`- Order ascending by score.` correctly, in a rules section 6 lines below the Output format section
that a session is actually reading while composing the block.

**The approved-pending patch**, which is P1's move-it-to-the-point-of-use fix and explicitly NOT a
reword. Append one sentence to `skills/rate-it/SKILL.md:107`, leaving line 113 as the canonical
rule:

> Then a blank line and a `**How to raise the score:**` block: 2-4 bullets, each a concrete change
> with the score it would unlock (e.g. `→ 7/10`). **Order the bullets by that score, lowest
> first.** Be specific [...]

Note the interaction with the cap fix above: that sentence lands on the same line whose `2-4` is
wrong, so do both edits in one pass and keep the numbers consistent.

**Verification** (the point of doing this in this repo rather than eyeballing it): eval fixture 5's
sixth expectation grades exactly this rule.

```
python tools/skill_eval.py --skill rate-it --label heal-ordering --parent v0-baseline-f5x3 --only 5 --repeat 3
```

At fewer than 3 repeats the run-to-run noise is as large as the patch, so a single run proves
nothing. Compare against `v0-baseline-f5x3` in `skills/rate-it/evals/history.json` (18/18), and
append the outcome to `heal-log.md` marking the entry applied and verified or applied and unproven.

## Notes

Two edits, one file, one section, one commit. Do not split them into two commits: a revert of one
without the other leaves line 107 self-inconsistent again.
