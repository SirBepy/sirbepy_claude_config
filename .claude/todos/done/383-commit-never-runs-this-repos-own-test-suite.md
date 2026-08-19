<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=9, reconfirm-count=1, content-hash=1c19496d -->
# /commit's test gate only looks for .claude/skills/run-tests/, so ~/.claude's own suite never runs

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit` run this repo's real test suite, so a commit that breaks `hooks/test_*.py` is caught
at commit time instead of days later.

## Context

**This gap shipped a broken test on 2026-08-18.** Commit `400d1e1` renamed `MARKER_GLOB` to
`MARKER_GLOBS` in `hooks/shortcut-create-guard.py` but did not update
`hooks/test_shortcut_create_guard.py`, which references it three times. The suite went red and the
commit landed anyway. It was only caught later, by accident, while reading that test file for an
unrelated reason, and fixed in `34c8e64`.

The verification floor in `CLAUDE.md` is unambiguous: *"Before claiming done or handing to Joe: run
every FAST check the project HAS (typecheck, unit, lint, build) - all must pass. No size exemption."*
`~/.claude` HAS such a check: **10 test files at `hooks/test_*.py`**, each self-contained, each
exiting 0/1, the whole set running in a couple of seconds.

**Why the skill did not catch it.** `skills/commit/SKILL.md` step 6 reads:

> Check if the repo has a project-level `run-tests` skill at `.claude/skills/run-tests/SKILL.md`.
> If yes, invoke it and wait for the result.

`~/.claude` has no `.claude/skills/run-tests/SKILL.md`, so step 6 finds nothing and passes silently.
The gate is keyed on a **skill existing**, not on **tests existing**. Any repo with real tests but
no wrapper skill gets zero test enforcement from `/commit`, and reports success while doing it.

Note this is the same shape as several live findings: a correct rule with nothing enforcing it for
one particular path. See [[356-prefilter-and-commit-in-one-shell-call-has-no-gate]] and
[[363-content-duplicate-guard-has-no-enforcement]].

## Approach

Two options, and the second is probably right:

1. **Create `.claude/skills/run-tests/SKILL.md` in `~/.claude`** that runs every `hooks/test_*.py`
   and fails on any non-zero exit. Smallest change, uses the mechanism that already exists, fixes
   only this repo.
2. **Widen step 6 itself** so that when no `run-tests` skill exists, `/commit` looks for an obvious
   suite before concluding there is nothing to run. Keep the detection mechanical and cheap, not a
   guess: a `test_*.py` / `*_test.py` set, a `test`/`check` script in `package.json`, a `tests/`
   directory with a runner config. Fixes every repo, and matches the hook doctrine in `PLAN.md`
   that exact mechanical checks ship while heuristic judgment calls do not.

Whichever is chosen, the failure must be **loud**: step 6 already says to abort the commit and print
the failing output, so the fix is in detection, not in the response.

## Acceptance

- Running `/commit` in `~/.claude` with a deliberately broken `hooks/test_*.py` aborts the commit and
  prints which suite failed.
- Running `/commit` in a repo with genuinely no tests still proceeds, and says so explicitly rather
  than silently, per the floor's *"if a project has no tests... say so explicitly instead of
  skipping quietly."*
- The check adds no meaningful time to a normal commit; the current 10 suites run in seconds.

## Notes

- Do NOT fold slow end-to-end suites into this. `CLAUDE.md`'s floor deliberately excludes them and
  projects opt in via `~/.claude/snippets/test-e2e.md`. This is about fast checks only.
- The suite to wire, verified passing 2026-08-18:
  `cd C:/Users/tecno/.claude/hooks; foreach ($t in Get-ChildItem -Filter "test_*.py") { python $t.FullName }`
- Related: [[382-shortcut-mutation-guard-has-no-test-file]] adds an 11th suite, which this gate would
  then also cover.
- c09b6c5: /commit step 6a detects a real suite (test_*.py, package.json test script, tests/ dir) when no run-tests skill exists, and aborts loudly on failure.
