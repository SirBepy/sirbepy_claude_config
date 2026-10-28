<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /commit's linter and run-tests checks got skipped without verification in a docs-only repo

**Type:** skill-improvement

## Goal

Close the gap where `/commit` steps 5 ("check if a linter exists") and 6 ("check for a
project-level run-tests skill") can silently get skipped without the executing agent actually
checking - it should be explicit that the repo was checked and found to have neither, not just
implicitly assumed.

## Context

`~/.claude/skills/commit/SKILL.md` step 5 says "Check if a linter exists - if yes, run it and fix
all issues first" and step 6 says "Check if the repo has a project-level `run-tests` skill at
`.claude/skills/run-tests/SKILL.md`. If yes, invoke it and wait for the result."

During a `/rate-it-and-commit` run on 2026-07-22 in this `.claude` skills repo (committing
`skills/close/ai-todos-format.md`, `skills/create-todo/SKILL.md`, `skills/handoff/SKILL.md`, then
`skills/rate-it/SKILL.md`, `skills/rate-it/panel.md`), the agent went straight from the
commit-style-override check to the submodule/shared-index checks and staged+committed - it never
ran an explicit check for a linter or a `run-tests` skill directory. In this specific case the
omission was harmless (this repo is pure Markdown skill files - no `package.json`, no linter
config, no `.claude/skills/run-tests/` directory exists), but the skip happened by assumption, not
by verification. A repo where that assumption is wrong (e.g. a project repo with an actual linter)
would get committed unchecked.

## Approach

Add an explicit early bail-out to steps 5-6 in `commit/SKILL.md`: before skipping either check,
actually glob/test for the relevant signal (a lint config file or `package.json` lint script for
step 5; the literal `.claude/skills/run-tests/SKILL.md` path for step 6) and only skip silently
once that check comes back negative. This makes "skipped because verified absent" and "skipped
because never checked" distinguishable in practice, even though the printed output looks the same
either way.

Rejected alternative: leave it as-is on the theory that it's "obviously fine" for docs-only repos
- that reasoning is exactly what makes the gap risky in a repo where it's NOT obviously fine.

## Acceptance

- `/commit`'s steps 5-6 name the concrete check to run (glob/test, not "check if" left vague)
  before concluding neither applies.
- A future session running `/commit` in a repo that DOES have a linter or run-tests skill can't
  skip past it by the same reasoning that was harmless here.

## Notes

Caught during this session's own `/close` retrospective (Phase 1, skill rule violation), not by
Joe - self-identified, not a correction from the dev.
- Dropped via /cleanup-todos 2026-08-11: step 6, the dangerous half, is already fixed; the remaining lint gap is cosmetic. Confirmed by dev 2026-08-11.
