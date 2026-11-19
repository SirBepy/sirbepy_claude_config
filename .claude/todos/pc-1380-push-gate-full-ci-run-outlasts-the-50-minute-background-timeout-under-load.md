<!-- Claim before executing: .claims/ per refs/ai-todos-format.md -->
<!-- duplicate-checked: grepped todos for 3000000 and run_all timeout; no existing todo covers the gate's CI launch budget -->
# Push gate: a full `python ci/run_all.py` outlasts the 50-minute background timeout when peers share the machine

**Type:** skill-improvement
**Origin:** ai
**Summary:** `skills/commit/push.md` tells the gate to launch the first background test run with `timeout: 3000000` (50 min), but on 2026-11-19 a full `ci/run_all.py` was killed at that limit and `test_todo_duplicate_guard.py` hit its own 120 s cap, so the gate had to re-run both pieces by hand.

## Context

- 2026-11-19 gate for 9 commits in `~/.claude`: `python ci/run_all.py` in the background with `timeout: 3000000` was killed at the limit while still inside the prefilter suites. Before that it reported `FAIL test_todo_duplicate_guard.py` (`TIMEOUT: exceeded 120s`, `ci/run_hook_tests.py` `TIMEOUT_SECONDS`), which passed in 75 s when run alone. `test_commit_pathspec.sh` hit its 1200 s budget (`ci/run_all.py`) in the same run and passed alone in 14 min 39 s. Other sessions were running CI at the time.
- `skills/commit/push.md` "Never lose a cargo run" says the first background launch gets `timeout: 3000000` and calls it the max; the Bash tool's maximum for a background command is 7200000 (commit 3df96f2 only reworded "Max" to "Long").

## Approach

1. In `skills/commit/push.md` give the first background launch of the repo's full unit-test command `timeout: 7200000`.
2. In `ci/run_hook_tests.py` raise `TIMEOUT_SECONDS` for the suites known to be slow under load (`test_todo_duplicate_guard.py`), or make the timeout a per-suite table, so a contended run is not reported as a failure.
3. Consider running `ci/run_all.py`'s checks as separate background tasks in the gate (hooks, tools, prefilter, skill scripts) so one slow suite never discards the others.

## Acceptance

A gate run with two other sessions running CI finishes without a TIMEOUT failure or a killed task, or reports exactly which suite is slow.
