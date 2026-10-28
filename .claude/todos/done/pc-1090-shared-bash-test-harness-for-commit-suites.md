<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=EASY, worth=3, reconfirm-count=1, content-hash=8d31e0fa -->
<!-- duplicate-checked: 2026-10-05; done/854 is the Python run_main shim in hooks/test_*.py, a different file family. No open todo covers the bash new_repo/check helpers. -->
# Share one bash test harness across skills/commit's three test suites

**Type:** task
**Origin:** ai

## Goal
`new_repo()` and `check()` are defined once and sourced by every `skills/commit/test_*.sh` suite.

## Context
Found by the 2026-10-05 pre-push /code-check (class 2). `skills/commit/test_split_hunks.sh:31,43`
(new in f582722) re-defines the scratch-repo and assertion helpers already defined near-identically
in `skills/commit/test_commit_pathspec.sh:15,30` and `skills/commit/test_prefilters.sh:24,41`.
done/854 deferred the same consolidation for the Python hook suites until another suite needed
it; this is the bash family's third copy.

## Approach
Create `skills/commit/test-harness.sh` with the two functions and `source` it from all three
suites. Keep each suite's own pass/fail summary line unchanged.

## Acceptance
- All three suites pass, and `python ci/run_all.py` passes.
- `grep -c 'new_repo()' skills/commit/test_*.sh` reports 0 definitions outside test-harness.sh.

## Notes

- Archived by /cleanup-todos 2026-10-06 (loop-todos cycle 2), worth 3: DRY-only test harness extraction, no incident.
