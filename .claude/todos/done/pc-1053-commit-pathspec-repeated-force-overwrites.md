<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=372febd2 -->
<!-- duplicate-checked: new finding about commit-pathspec.sh flag parsing -->
# commit-pathspec.sh: a second --force silently replaces the first

**Type:** skill-improvement
**Origin:** ai

## Goal

`--force overlap --force foreign-hunk` either accumulates both, or errors out loudly. It must never quietly honour only the last one.

## Context

Found 2026-09-30 in a claude_usage_in_taskbar autopilot run. `skills/commit/commit-pathspec.sh:84`
parses `--force) force_list="${2:-}"; shift 2 ;;`, so a repeated `--force` overwrites the earlier value.
The run passed `--force overlap --force foreign-hunk` several times. It worked only while no overlap hit
occurred. The first real overlap refused the commit with "[overlap-check] REFUSED" even though
`overlap` had been passed. It took a rerun with `--force overlap,foreign-hunk` to get past. The usage
line documents the comma form, but the repeated-flag form is what a caller naturally writes, and
nothing warned.

## Approach

In the arg loop, append instead of assign: `force_list="${force_list:+$force_list,}${2:-}"`. Keep the
comma form working. Add a self-test case in the commit skill's test suite, if one exists, or in
`ci/run_all.py`'s coverage.

## Acceptance

- `--force overlap --force foreign-hunk` proceeds past both checks.
- `--force overlap,foreign-hunk` still works.
- `python ci/run_all.py` is green.

## Notes

- Completed by /loop-todos cycle 1 (2026-10-05), lane B, test-first in skills/commit/test_commit_pathspec.sh (11 new assertions RED against HEAD, 57/57 GREEN).
