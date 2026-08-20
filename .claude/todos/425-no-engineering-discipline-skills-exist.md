<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# There are 83 skills and not one engineering-discipline skill

**Type:** task
**Origin:** ai

## Goal

Fill the single biggest capability gap found in the harvest: no TDD skill, no refactoring method, no
debugging methodology, no mutation testing, no way to safely touch untested code.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

The 83 skills here are overwhelmingly workflow and tooling: commit, PR, todos, session lifecycle,
Figma, Flutter, Cloudflare, screenshots, memory. **The entire engineering-discipline category is
absent.** CLAUDE.md has rules that gesture at it ("no drive-by refactors", the testing floor, "define
success criteria upfront") but no skill provides a method for any of them.

`citypaul/.dotfiles` (715 stars, 360 commits, a real daily driver) has 47 skills covering exactly
this. Full list at `repos/citypaul_.dotfiles/claude/dot-claude/skills/`: acceptance-review, api-design,
bff-design, bff-entry-points, characterisation-tests, ci-debugging, cli-design, codebase-design,
debugging, diagrams, domain-driven-design, double-check, evaluate-existing-solutions, event-sourcing,
expectations, find-gaps, find-skills, finding-seams, folder-structure, front-end-testing, functional,
graph-engineering, hexagonal-architecture, improve-codebase-architecture, mutation-testing,
observability, panel-review, planning, production-parity-skill-builder, react-performance,
react-testing, reduce-system-complexity, refactoring, render-code-shape, secure-oauth-oidc,
specification, stack-pull-requests, story-splitting, storyboard, structure-codebase, tdd, teach-me,
technical-writing, test-design-reviewer, testing, twelve-factor, typescript-strict,
ubiquitous-language, wtf, xstate.

The five worth taking first, with the specific reason each one earns its place:

1. **tdd** - RED-GREEN-REFACTOR as a governing workflow with an explicit mutation gate at end of
   phase. There is zero test-first discipline today; `/code-check` only reviews after the fact.
2. **refactoring** - behavior-preserving-change classification that requires starting from a passing
   baseline with proportionate preservation evidence. Fills the gap between the "no drive-by
   refactors" rule and any actual method for doing one safely.
3. **mutation-testing** - a Stryker-based survivor-killing gate. The testing floor runs existing
   tests but never checks whether those tests would catch a real regression, which is the difference
   between having tests and being covered.
4. **debugging** - preserve evidence, one causal hypothesis at a time, fix the owning boundary. Note
   the harness already offers a `systematic-debugging` skill from another source, so compare before
   adopting a second one.
5. **characterisation-tests** - pin down what untested code actually does before changing it. Directly
   useful given the amount of personal tooling here with no test floor of its own.

Two dependencies worth knowing:

- **Todo 421 wants this.** `panel-review`'s design uses installed skills as review lenses. With no
  engineering-discipline skills installed, option (b) in 421's approach is unavailable. Landing this
  first makes 421 strictly better.
- Several of these skills are **stack-specific** (react-performance, xstate, typescript-strict,
  hexagonal-architecture, DDD, event-sourcing). Adopting a hexagonal-architecture skill when no
  project uses hexagonal architecture is pure description-budget cost with no upside, and CLAUDE.md's
  own execution-discipline rules warn against exactly that kind of unrequested surface. Be selective.

Description-budget constraint: todo 400 (live) is about two model-invocable skill descriptions already
being over budget, and a memory entry records that `disable-model-invocation` skills are excluded
from the listing entirely. Adding 5 model-invocable skills has a real cost in that listing; consider
whether some should be explicitly invoked only.

## Approach

1. Read the 5 target SKILL.md files in the corpus in full. They are written for a TypeScript/React
   shop; assess honestly how much is transferable versus stack-bound.
2. Do NOT bulk-copy. For each of the 5, decide: adopt close to as-is, adapt heavily, or skip. Write
   the decision and the reason. A skill adopted without adaptation that references tooling not
   installed here is worse than no skill.
3. Check for collisions first. The harness already exposes `systematic-debugging` and `tdd` from
   other sources in some sessions, and `/code-check` and `/test` already cover adjacent ground. Two
   overlapping skills is a triggering problem, not a bonus.
4. Adapt for the real stacks in use: Flutter/Dart, TypeScript/React, Rust/Tauri, Luau. `mutation-testing`
   assumes Stryker, which is JS-only, so the Dart and Rust story needs to be written or the skill
   needs to say it is JS-scoped.
5. Adopt them one at a time, and pilot each on real work before adding the next. The 2026-08-01 skill
   audit deleted 12 skills; adding 5 unproven ones straight into the listing repeats whatever caused
   that.
6. Feed the result back to todo 421 if lenses-as-skills becomes viable.

## Acceptance

- For each of the 5, a written adopt/adapt/skip decision with a stated reason.
- Every adopted skill has been used on one real task, and that is reported with what it changed, not
  just that it was installed.
- No adopted skill references tooling that is not installed, or it explicitly scopes itself to the
  stack where that tooling exists.
- No adopted skill duplicates an existing skill's trigger surface; overlaps are named and resolved.
- The model-invocable description budget is checked against todo 400's constraint.

## Notes

The temptation here is to take all 47. Do not. That repo's owner built them over 360 commits against
one stack he works in daily; most are load-bearing for him and dead weight here.

`panel-review` and `graph-engineering` from the same repo are handled by todo 421, not this one.

If `tdd` turns out to conflict with how work actually gets done here (much of this repo is prose,
config and hooks rather than testable application code), say so. A TDD skill that never fires
honestly is a finding, not a failure.

**SETTLED 2026-08-20 by Joe, do not re-litigate. Two of the five are downgraded:**

- **Item 2, `refactoring`: GATED on todo 451, and likely dropped.** Joe: *"we have todos, they get
  made by code-check and it suggests refactoring right? keep in mind i never end up rly reading the
  code... so... i dont even ask for the refactor."* This todo's original argument was that CLAUDE.md
  has a no-drive-by-refactors rule with no method behind it. That argument assumed someone drains the
  refactor queue. Nobody does. Adopting a refactoring skill behind a queue that never drains is
  motion, not progress. **Do not adopt it until 451's classification shows there is a class of
  finding that actually reaches execution.**
- **Item 5, `characterisation-tests`: LOW priority.** Joe's pushback: *"couldnt we just make AIs
  document their code better and then that way we dont have to have the AI have to rediscover what
  the code does?"* Mostly right. The distinction that survives: documentation records **intent**,
  tests record **actual behavior including the bugs**, and docs drift silently while a test cannot,
  because it runs. The concrete proof is in this very backlog: **todo 414 is a hook whose docstring
  says it is "not wired into settings.json yet" while `settings.json` wires it.** So the split is
  document-for-intent by default (cheap, do it), characterisation tests only when about to change
  untested code that cannot afford to break.

Items 1 (`tdd`), 3 (`mutation-testing`) and 4 (`debugging`) are unaffected and remain the real targets.

For context on why the review timing matters at all here, read todos 450 and 451 first: Joe's stated
reason `/code-check` runs late is that **AI is very bad at reviewing its own code**, which is a
constraint to design around, not a bug to fix.
