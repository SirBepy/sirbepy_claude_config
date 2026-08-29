<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=5, reconfirm-count=1, content-hash=5579d4f9 -->
<!-- duplicate-checked -->
# skills/wrangler/SKILL.md is 923 lines, 2.5x the next largest skill

**Type:** skill-improvement
**Origin:** ai

## Goal

Move the bulk of `/wrangler` into sidecar files that are read on demand, so invoking it stops
loading 923 lines of context to answer a question that needs twenty of them.

## Context

Found 2026-08-21 by the progressive-disclosure audit that todo 422 asked for. Measured line counts
of all 85 `skills/*/SKILL.md`:

```
923  wrangler
372  mega-todos
361  cleanup-todos
331  turnstile-spin
316  zirtue-release-backfill
305  auto-do-todos
287  create-pr
```

`wrangler` is the only real outlier: 2.5x the next largest and 6x the median. Everything else is
already in range, and **the sidecar convention is already the local norm** (`rate-it/panel.md`,
`iterate-it/templates.md`, `close/*.md`, `commit/*.md`, and 20+ others), so this is one file out of
step rather than a convention to introduce. `bepy-skill-creator`'s own WARN rules already say heavy
flag flows belong in sidecars and that 4+ sidecars means the skill is too broad, which is the
tension to resolve here.

Anthropic's own published skills are the outside evidence for the same shape: `mcp-builder` carries
a 236-line SKILL.md against 2,537 lines of `reference/`, and `webapp-testing/SKILL.md` states the
rule outright, that its scripts exist to be called as black boxes rather than read into context.

Nothing was refactored as part of 422: a split is a behavior risk on a skill nobody has fixtures
for, and 422's own scope was the harness plus one pilot.

## Approach

1. Read `skills/wrangler/SKILL.md` and group its sections by when they are actually needed.
2. Split by that grouping, not by size. SKILL.md keeps the trigger, the argument grammar, the
   workflow spine and one pointer line per sidecar.
3. Watch the sidecar count. If the honest split needs 4 or more, that is `bepy-skill-creator`'s own
   signal that `/wrangler` should be several skills, and that is the finding to report rather than
   spawning five files.
4. State the before and after line counts. 422's acceptance asked for exactly that, and this todo
   inherits it.

## Acceptance

- `skills/wrangler/SKILL.md` is materially smaller, with the before and after counts stated.
- Behavior is identical: every instruction that left SKILL.md is reachable from a pointer line in
  it, and no instruction is dropped in the move.
- `python ci/run_all.py` exits 0 (skill frontmatter validation covers all 85 skills).
- Sidecar count stays under 4, or the report says why `/wrangler` should be split into several
  skills instead.

## Notes

Consider writing eval fixtures for `/wrangler` first (`tools/skill_eval.py`, see `skills/rate-it/
evals/` for the shape). A 923-line-to-sidecar split is exactly the change where "behavior is
identical" is asserted and not checked, and this is now the one repo where it can be measured.
