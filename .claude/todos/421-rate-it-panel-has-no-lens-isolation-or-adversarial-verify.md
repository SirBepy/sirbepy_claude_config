<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /rate-it's panel has no lens isolation and no adversarial re-verify, which is why scores go flat

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix the structural cause of `/rate-it`'s known flat-score failure mode by giving each panel agent a
single fixed review lens and adding an independent adversarial verification pass before synthesis.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`). This is the highest-
value skill finding in the whole corpus, because it names a mechanism for a failure already recorded
in memory rather than proposing a new feature.

The known symptom, already in auto-memory as "Rate-panel diminishing returns": a flat score across
rounds while each round surfaces DIFFERENT bugs. That memory concluded flat-score-with-different-bugs
means stop and ship, which is a reasonable operating heuristic. The harvest suggests it is also a
symptom of panel architecture, not just convergence.

`citypaul/.dotfiles` `panel-review` (`repos/citypaul_.dotfiles/claude/dot-claude/skills/panel-review/`,
built on its `graph-engineering` skill) does three things `/rate-it` does not:

1. **One skill per lens.** Each sub-agent loads exactly ONE named skill as its review lens
   (hexagonal-architecture, typescript-strict, structure-codebase, and so on), so each reviewer
   judges against a fixed external standard rather than forming a holistic opinion. Lenses are
   selected by project-trait detection plus explicit user choice.
2. **Adversarial re-verification before synthesis.** Findings from the fan-out are re-checked by an
   independent node whose job is to refute them, and only survivors reach the report.
3. **`unverifiable` is a distinct outcome from `refuted`.** Nothing gets averaged away.

`/rate-it` and `/iterate-it` currently fan out agents that each form a holistic judgment and return a
number, then average or synthesize. With no lens isolation, every agent is looking at the same thing
the same way, so they converge on the same score while noticing different details. With no adversarial
pass, nothing filters a plausible-but-wrong finding. **That is exactly the shape that produces a
stable score over a shifting finding set.**

`solatis/claude-config`'s `decision-critic` contributes two smaller pieces worth taking:

- **Claim-level falsification answered BLIND to the decision** - the verifier is explicitly told not
  to look at the synthesis while answering, which removes the anchoring that makes a reviewer agree
  with what it just read.
- **A STAND / REVISE / ESCALATE verdict rubric** instead of a bare number.

`decision-critic` is weaker where `/rate-it` is already strong: it runs everything in one context
with no fresh sub-agent, while `/rate-it` can spawn a real N-agent panel. So the move is to graft
its verification discipline onto the existing dispatch machinery, **not** to swap mechanisms.

Prior art in `done/` to read before touching anything, so settled decisions are not re-litigated:
221 (rate-it panel md skill path), 241 (drop research flags), 251 (no-tool-call rule unsatisfiable in
Conductor), 268 (rate-it suggests iterate-it for design lifts), 373 (rate-it panel dispatch fails the
preamble guard), 230 (iterate-it phase A to B audit gate), 253 (iterate-it enforce report final
message).

## Approach

1. Read `panel-review/SKILL.md` and `graph-engineering/SKILL.md` in the corpus, plus
   `solatis/.../decision_critic`. Then read the current `skills/rate-it/` and `skills/iterate-it/`
   in full.
2. Decide the lens question first, because everything else depends on it, and it is a genuine fork
   worth surfacing to the dev rather than picking silently: `panel-review` uses *installed skills* as
   lenses, and this setup has 83 skills but almost no engineering-discipline ones (see todo 425). So
   either (a) lenses are named review dimensions defined inside `/rate-it` itself, or (b) lenses are
   skills, which makes this todo depend on 425 landing first. Option (a) is available now; option (b)
   is stronger later.
3. Add the adversarial verification pass. This is the part that can be done independently of the lens
   question and is likely the bigger win on its own: after the fan-out, dispatch verifiers whose brief
   is to REFUTE each finding, and keep only survivors. The delegation doctrine already describes this
   pattern for high-stakes diffs; `/rate-it` does not use it.
4. Add the blind-verification constraint: a verifier must not see the synthesis or the other agents'
   scores while answering.
5. Replace or supplement the bare numeric score with a STAND / REVISE / ESCALATE verdict, and keep
   `unverifiable` distinct from `refuted`. Note the existing convention from memory: scores are
   reported as N/10 with the threshold stated separately, never N/N. Whatever replaces or joins the
   number must not break `/rate-it-and-commit`'s threshold comparison.
6. Verify against the actual symptom, which is the only acceptance test that means anything here:
   find a change where `/rate-it` previously returned a flat score across rounds, re-run the new
   panel on it, and check whether the score now moves or whether the findings are now filtered.

## Acceptance

- Each panel agent receives exactly one review lens, and the lens is stated in its dispatch prompt.
- An adversarial verification pass runs between fan-out and synthesis, and its refutations are
  visible in the output.
- Verifiers demonstrably do not see the synthesis (check the dispatch prompts, not the intent).
- `unverifiable` and `refuted` are distinct outcomes in the report.
- `/rate-it-and-commit` still works: its threshold gate reads whatever the new output format is.
- Re-run on a known flat-score case and report what actually changed. If the score is still flat,
  say so plainly rather than declaring victory on structure alone.

## Notes

Do not delete the numeric score. `/rate-it-and-commit` depends on it and the dev reads it.

Do not swap `/rate-it`'s dispatch machinery for `decision-critic`'s single-context script engine.
Single-context verification is strictly weaker than a fresh sub-agent; only the blind-answering
discipline and the verdict rubric are worth taking from it.

Be honest in the final report about which of the three changes actually moved the needle. Shipping all
three and claiming the improvement is exactly the unverified-mechanism trap.
