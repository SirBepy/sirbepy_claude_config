<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/842 is what CAUSED this, and it is closed; nothing in the backlog or
     done/ covers the budget gate itself or its missing enforcement -->
# Twelve skill descriptions went over budget in one pass, and no check can see it

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether the ~25 word / 120 char description budget still binds a skill that a parent flow
invokes, then either bring the twelve over-budget descriptions back under it or write down why they
are exempt. Either way, make the gate mechanical so the next drift is caught.

## Context

Found 2026-09-10 by `/close` Phase 2's independent review of that session's own 38 commits.

`done/842-eighteen-skills-declare-slash-only-but-are-model-invocable.md` deleted the false "Triggers
on /X only." sentence from 13 skill descriptions and replaced it with a real description of what
each skill does. That fix was correct: the sentence was a lie, and 11 of those skills are genuine
chain callees that would have broken had they been flagged instead.

The cost landed somewhere nobody looked. A skill `description` loads into EVERY session's system
prompt, so its length is a per-session token charge on every project. `skills/bepy-skill-creator/SKILL.md`
carries a WARN row for exactly this: *"`description` is within the budget gate (~25 words / 120
chars), unless a trigger keyword forces it over"*.

Measured after the change, independently confirmed rather than taken from the review:

| skill | after | before |
|---|---|---|
| `apply-styleguide` | 28 words / 194 chars | 4w / 35c |
| `pwa` | 28w / 174c | 4w / 22c |
| `isolated-build` (new file) | 32w / 187c | n/a |
| `github-pages-init` | 23w / 155c | 4w / 36c |
| `meta-tags` | 20w / 152c | 4w / 28c |
| `favicon` | 23w / 146c | 4w / 26c |
| `inject-widgets` | 19w / 145c | 4w / 33c |
| `init-claude-md` | 17w / 131c | 4w / 33c |

Plus four that were already over and got worse: `iterate-it` (43w to 50w), `rate-it` (40w to 44w),
`batch-todos` (18w to 27w), `cleanup-todos` (22w to 31w).

**Nothing catches this.** `ci/check_skill_frontmatter.py` validates YAML structure and required
keys only; it never counts words or characters, confirmed by reading it. So `ci/run_all.py` was
green through the whole change.

## Approach

1. **Settle the policy question first, because it decides the work.** The old descriptions were
   short because they said almost nothing ("Triggers on /X only" plus four words). A skill that a
   parent flow invokes needs enough description for the MODEL to pick it, which is what 842 was
   fixing. So either the budget is too tight for that class of skill, or these twelve need real
   trimming. Do not start editing before answering this.
2. If the budget stands: trim the twelve to the trigger surface, preserving every keyword that makes
   the skill findable. Check each against its callers first - a description that no longer matches
   how a parent flow describes the step is worse than a long one.
3. If the budget should relax for chain-invoked skills: write the carve-out into
   `skills/bepy-skill-creator/SKILL.md`'s checklist with its boundary stated, so the next reviewer
   does not re-flag these twelve.
4. Either way, add the length check to `ci/check_skill_frontmatter.py` so this is mechanical. It
   already reads every skill's frontmatter, so the marginal cost is a word count and a threshold.
   Whatever step 1 decides is what the check enforces.

## Acceptance

- Every skill description is either within budget or covered by a written, bounded exemption.
- `ci/check_skill_frontmatter.py` fails on a description that breaches whichever rule step 1 settles.
- `python ci/run_all.py` exits 0.

## Notes

- Do not "fix" this by reverting to "Triggers on /X only". That sentence was false for 11 of these
  skills and 842 removed it deliberately; see its `done/` entry for which skills invoke which.
- The review that found this classed it mechanical, but it is not: trimming a description can change
  which skill the model picks, and there is no test that would fail if a trim went wrong. That is
  why it is filed rather than applied.
