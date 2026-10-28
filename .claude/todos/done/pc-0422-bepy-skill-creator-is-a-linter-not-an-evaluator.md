<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# bepy-skill-creator lints conventions but cannot tell whether a skill edit helped

**Type:** skill-improvement
**Origin:** ai

## Goal

Add an eval loop to skill authoring so a change to one of the 83 skills can be measured against
fixtures instead of judged by reading it.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`). Anthropic's own
`skill-creator` is the reference, which makes this the highest-authority finding in the corpus.

`repos/anthropics_skills/skills/skill-creator/` ships:
- `evals/evals.json` - eval fixtures for the skill being developed
- `agents/grader.md` (223 lines) - an **independent** grader agent that scores pass rate, kept
  separate from the agent that produced the work
- `agents/analyzer.md` (274 lines) and `agents/comparator.md` (202 lines)
- `history.json` - version lineage, tracking v0 to v1 to v2 with each marked "won" or "baseline"
- `scripts/run_loop.py` - automates iterate-and-compare
- `improve_description.py` - tunes the `description` field specifically, for triggering accuracy
- `references/schemas.md` (430 lines), never loaded into context

`bepy-skill-creator` creates, validates and fixes skills against conventions. That is a **linter**.
It checks structural conformance and cannot answer the only question that matters after an edit: did
the skill get better at its job?

With 83 skills, several of which have been revised repeatedly (`/rate-it` alone has seven todos in
`done/`), there is currently no way to know whether any of those revisions helped. Todo 421 makes
this concrete: it proposes three changes to `/rate-it` and its acceptance criteria have to fall back
on "re-run on a known case and report what changed", because no measurement harness exists.

The description-tuning piece connects to a live todo: **400 (two model-invocable skill descriptions
over budget)** is about description length. `improve_description.py` is about description *triggering
accuracy*, which is the same field for a different reason. Read 400 before touching descriptions so
the two do not fight.

Also relevant from the same repo, and cheaper to adopt than the eval loop: the official skills use
**only `name`, `description` and `license`** in frontmatter across all 18 examples, and they push bulk
into `references/` and `scripts/` that are never loaded (mcp-builder's `reference/` is 2537 lines
against a 236-line SKILL.md). `webapp-testing/SKILL.md` states the rule outright: "DO NOT read the
source until you try running the script first... These scripts exist to be called directly as
black-box scripts rather than ingested into your context window."

## Approach

1. Read `repos/anthropics_skills/skills/skill-creator/` in full: the three agent files, the schemas
   reference, `run_loop.py`, and `improve_description.py`.
2. Decide scope honestly before building, since the full harness is a lot of machinery for a solo
   setup. The three pieces in increasing cost:
   - **Eval fixtures plus an independent grader** - the core value. A skill gets a small set of
     input cases and expected outcomes; a separate agent scores them.
   - **Version lineage (`history.json`)** - cheap, and it is what makes "did this help" answerable
     across sessions rather than within one.
   - **`run_loop.py` automation** - most expensive, least necessary at this scale. Probably skip
     until the first two prove useful.
   Recommend starting with fixtures plus grader for a SINGLE skill as a pilot, not all 83.
3. Pick the pilot skill deliberately. `/rate-it` is the obvious candidate because todo 421 needs
   exactly this measurement, and because its failure mode is already characterized.
4. Keep the grader genuinely independent. The doctrine already warns that a check whose construction
   guarantees a pass proves nothing; a grader that sees the authoring agent's reasoning is that
   failure. Deny it the rubric the author saw, the way `serpro69/claude-toolbox`'s `eval-grader`
   does (also in the corpus, `klaude-plugin/agents/eval-grader.md`).
5. Separately and independently of the eval work, adopt the progressive-disclosure convention: audit
   whether any current SKILL.md is carrying bulk that belongs in a `references/` file. This is a
   cheap win and does not depend on the harness.

## Acceptance

- One skill has eval fixtures and an independent grader, and the grader produces a pass rate.
- The grader provably does not see what the authoring agent saw (inspect its dispatch, not the intent).
- A deliberate regression to the pilot skill is caught by the harness. If it is not caught, the
  fixtures are not testing anything and that must be reported rather than papered over.
- Version lineage records at least a baseline and one revision with a won/lost verdict.
- Any progressive-disclosure refactor keeps behavior identical, with the SKILL.md line count before
  and after stated.

## Notes

Do not build the full official harness. It is sized for a team publishing skills publicly; this is
one person with one repo. Fixtures plus an independent grader is the 80%.

Do not start by writing fixtures for all 83 skills. That is a week of work producing fixtures nobody
validated. One pilot, proven, then decide.

Note the tension with the earlier scout claim: `context: fork`, `allowed-tools`, `paths:` and
`model:` were reported as underexploited frontmatter fields, but Anthropic's own examples use none of
them. Available is not the same as recommended.

**SETTLED 2026-08-20 by Joe, do not re-litigate: WRAP, do not replace.** He asked whether to stop
using `bepy-skill-creator` or have it call Anthropic's `skill-creator` instead. The answer is the
second one, layered:

- `bepy-skill-creator` keeps owning **"does this match bepy conventions"**. Those conventions are
  Joe's own and are the reason the skill exists; deleting it would throw away the part no upstream
  tool can supply.
- The eval loop is the part that is genuinely missing, and it answers a different question:
  **"did this edit actually make the skill better at its job"**.

So the shape is `bepy-skill-creator` gaining a handoff step to the eval harness, not being retired
and not being rewritten around upstream. Do not delete or deprecate `bepy-skill-creator` as part of
this todo.
- Shipped 2026-08-21. tools/skill_eval.py runs each fixture in a fresh `claude -p` process, then grades it in a second process launched with Read/Write/Edit/Bash/Task denied; tools/test_skill_eval.py (18 offline checks, wired into CI by ci/run_tool_tests.py) proves no grader prompt echoes any 12-word run of the skill own instructions, so independence is checked, not asserted. The first TWO deliberate regressions were NOT caught (anti-sycophancy cut: 100 vs 100 percent; how-to-raise cut: mutant WON at 93.3 vs 86.7). Cause: fixture 5 graded conditional behaviour unconditionally, so correct use of the no-lift escape hatch failed 4 of 6 assertions and the fixture own variance ran 6/6 to 1/6. With those assertions made conditional (fixture set v4) the same mutation is caught cleanly: 18/18 baseline vs 11/18 mutant over 3 repeats, verdict lost, one assertion going 3/3 to 0/3. Side finding, a real live defect: /rate-it violates its own documented "Order ascending by score" rule in 2 of the 3 recorded runs that produced two or more scored bullets (5 runs total, 2 of them used the no-lift hatch and produced none; corrected 2026-08-22 from an earlier "4 of 6" that had wrongly counted mutated-skill runs and one reused response) (material for 436). Progressive-disclosure audit done, nothing refactored: sidecars are already the local convention, the one outlier is skills/wrangler/SKILL.md at 923 lines, filed separately. Full lineage in skills/rate-it/evals/history.json (9 runs). Spend about 17 USD.
