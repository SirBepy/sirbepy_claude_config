<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=7, reconfirm-count=1, content-hash=dd373c8a -->
<!-- duplicate-checked: 1073 (done) is the staged-pathspec [coverage-check] basename false positive; this is the separate [coverage-tests-check] test-file classifier. 1045/1137 (done) moved the client list and extension lists, not is_test_path's patterns. -->
# commit-pathspec's coverage-tests check misses a repo's verify/ probes

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `[coverage-tests-check]` from refusing a commit that does ship its test, just because that
repo names tests differently from the hardcoded patterns.

## Context

`skills/commit/commit-pathspec.sh` `is_test_path` (around line 741) counts a file as a test only
when its basename matches `test_*`, `*_test.*`, `*.test.*` or `*.spec.*`, or when its path has a
`test/`, `tests/`, `__tests__/` or `spec/` segment.

countoff keeps all of its tests under `verify/` as `*-probe.cjs` and `*-unit.mjs`. On 2026-10-08,
an unattended `/loop-todos` run committed `c9c6ac8` in countoff. That commit shipped a new unit
test (`verify/dropped-work-unit.mjs`) and a new emulator probe (`verify/stale-device-probe.cjs`)
next to the fix, and the check still refused it. The same night, `--force coverage-tests` was needed
on all 7 commits, including three that did carry a test (`c9c6ac8`, `b1457d5`, `a3177fb`). Once the override is routine, it stops
meaning "this change is untestable", which is the only thing it is supposed to say. Todo 1073 found
the same dulling for the sibling `[coverage-check]`.

## Approach

- Add a `*/verify/*` path pattern, plus `*-probe.*` and `*-unit.*` basename patterns. Alternatively,
  read a per-repo override such as a `testPathPatterns` line in `.claude/commit-style.md`, so each
  repo can declare its own convention.
- Pure refactors still need the override. That is correct, so leave it alone.
- Test-first in `skills/commit/test_commit_pathspec.sh`, where 1073's assertions already live.

## Acceptance

- A pathspec of `src/lib/a.ts verify/a-unit.mjs` passes `[coverage-tests-check]` without
  `--force`.
- A pathspec of `src/lib/a.ts` alone is still refused.
- `python ci/run_all.py` is green.
