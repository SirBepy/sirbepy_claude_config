<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=EASY, worth=7, reconfirm-count=1, content-hash=45ac5a46 -->
# Concurrent ci/run_all.py runs flake two test suites

**Type:** task
**Origin:** ai

## Goal

`python ci/run_all.py` gives the same verdict whether it runs alone or alongside other runs of
itself in the same checkout, so a parallel builder fan-out never reports a false red.

## Context

2026-10-05 /loop-todos cycle 1, up to 6 builders each ran `ci/run_all.py` concurrently in
`C:\Users\tecno\.claude`. Several builders reported transient failures that passed clean on rerun:

- `skills/commit/test_commit_pathspec.sh` hit run_all's own 120s per-suite `TimeoutExpired` under
  contention (it is the slowest suite, ~70 cases each building scratch repos).
- `tools/test_close_reserve_todo_id.py` failed once on its 24h-boundary / legacy-marker case.
- `hooks/test_secret_write_guard.py` (`.env.example` placeholder case) failed once.

One builder also force-killed other builders' `run_all.py` processes while cleaning up its own,
which is a separate habit problem but was triggered by the slow, overlapping runs.

## Approach

1. Give `check_prefilter_suites` (ci/run_all.py) a per-suite timeout sized to the slowest suite's
   real runtime plus headroom, or make it configurable.
2. Make the reserve-todo-id boundary case independent of wall-clock timing (inject the clock or
   use mtimes far from the threshold).
3. Re-run the secret-write-guard case 20x in parallel to see whether it is order- or
   shared-file-dependent before changing it.

## Acceptance

- Six concurrent `python ci/run_all.py` invocations all report "OK: all 6 checks passed".
- No suite's verdict depends on another run's scratch files.

## Notes

- Done in loop-todos cycle 2 (2026-10-06): check_skill_tests timeout 120 -> 600; reserve-todo-id.ps1 takes an injectable -Now so the boundary test pins one clock instead of racing wall time; the secret-write-guard missing-patterns test runs a temp copy of the hook instead of renaming the shared secret-patterns.txt. Each suite passes 3x sequential and 5x concurrent; the 6-way concurrent run_all acceptance runs at the Phase 2 gate.
