# rate-it heal log

One bullet per `/heal-skill` run. A second entry naming the same symptom means the earlier patch did
not work and its diagnosis was wrong. Read this before diagnosing anything here.

- **2026-08-22, PROPOSED, awaiting the dev's approval.** Symptom: the How-to-raise bullets are not
  ordered by unlocked score. Observed as `6/10, 5/10, 6/10` and `6/10, 5/10` in 2 of the 3 recorded
  eval runs that produced two or more scored bullets (5 runs total; 2 used the no-lift hatch and
  produced none). Pattern **P1**, the rule depends on being remembered: `SKILL.md:113` states
  "Order ascending by score." correctly, in a rules section 6 lines below the Output format section
  that a session is actually reading while composing the block. Proposed patch, P1's
  move-it-to-the-point-of-use fix rather than a reword: append `Order the bullets by that score,
  lowest first.` to `SKILL.md:107`, leaving the canonical rule in place. Not applied: `/heal-skill`
  step 6 requires approval first. Verifiable through eval fixture 5, whose sixth expectation grades
  exactly this, at `--repeat 3` or more.
- **2026-08-22, separate finding, filed not patched.** `SKILL.md:107` allows 2-4 bullets while
  `SKILL.md:114` caps them at 3. Pattern **P6**. Filed as todo 475 rather than folded in here, since
  one run diagnoses one cause.
- **2026-08-31, APPLIED, both edits landed in one commit (todo 475).** Cap fix: `SKILL.md:113` now
  reads "up to 3 bullets", matching the "Cap at 3 bullets" rule. Ordering fix: appended "Order the
  bullets by that score, lowest first." to the same line, per the approved-pending patch above.
  Verification: `python tools/skill_eval.py --skill rate-it --label heal-ordering --parent
  v0-baseline-f5x3 --only 5 --repeat 3` against `v0-baseline-f5x3` (18/18). Result: 15/18
  (pass_rate=83.33%), verdict=incomparable. The cap expectation (n=2, "at most 3 suggested
  improvements") held stable at 3/3, matching baseline - that half is verified. The ordering
  expectation (n=6) passed only 2/3 (rep1 still produced descending order 8/10, 7/10, 6/10),
  versus baseline's 3/3 - **applied and unproven**, not applied and verified. The move-to-point-
  of-use fix did not fully eliminate the ordering miss in this run. Also observed: n=4 (cost/
  tradeoff) dropped to 1/3, unrelated to this todo's edits - out of scope, not investigated here.
