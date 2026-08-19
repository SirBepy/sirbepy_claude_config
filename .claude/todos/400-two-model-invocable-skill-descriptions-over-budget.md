<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Two model-invocable skill descriptions are over the always-on budget

**Type:** skill-improvement
**Origin:** ai

## Goal

Trim `skills/flutter-e2e/SKILL.md` and `skills/linear/SKILL.md`'s `description:` frontmatter to the
~25-word trigger surface, without cutting any clause that makes the skill fire.

## Context

Both are model-invocable (no `disable-model-invocation` flag), so their descriptions load into every
session's system prompt and are paid for on every single session, whether or not the skill is used.
Measured 2026-08-19 during a `/code-check` pass:

- `skills/flutter-e2e/SKILL.md:3` - **63 words, 407 chars**, roughly 2.5x the budget. The bulk is
  mode detail that carries no trigger signal: "scripted mode (raw Playwright, release build,
  optional Firebase-emulator layer) or plan-file mode (steps through a markdown test plan, marking
  pass/fail/skip inline)". That already lives in the skill body.
- `skills/linear/SKILL.md:3` - **30 words, 167 chars**, moderately over. Candidates: shorten
  "search, list, look up, or file issues", and fold the trailing "Writes are tightly scoped - see
  the Write rules" into the body.

Neither `description:` line was touched by the 2026-08-19 mega-todos run (verified with `git diff
002760e..HEAD` on both files), so this predates it.

For scale: the 2026-08-18 skills audit cut the per-session description budget from 10,445 to 5,892
chars by flagging 13 skills slash-only. `flutter-e2e` alone is 407 of the remaining 5,892.

## Approach

1. Keep every quoted trigger phrase and when-to-use keyword. The budget gate exists to cut
   elaboration, never trigger surface: a skill that stops firing is a worse outcome than a long
   description.
2. For `flutter-e2e`, keep the three quoted trigger phrases and the `/test-flow` alias clause; cut
   the two mode parentheticals.
3. Consider whether either should be slash-only instead, which zeroes the cost outright. That is a
   bigger call than trimming and needs the dev, so raise it rather than deciding it.

## Acceptance

- Both descriptions are at or near ~25 words.
- Every trigger phrase that existed before still exists.
- The two skills still fire on their documented triggers.
