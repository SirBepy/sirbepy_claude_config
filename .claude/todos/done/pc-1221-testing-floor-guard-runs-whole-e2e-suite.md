<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# testing-floor-guard runs an edited e2e .mjs as a script and blocks the turn on ECONNREFUSED

**Type:** task
**Origin:** ai

## Goal

Editing a file under a project's `e2e/` folder no longer makes the Stop-hook testing floor fail the turn three times because no game server is running.

## Context

Seen 2026-10-22 in `C:\Users\tecno\Desktop\Projects\mc_plugins_tag`. After a commit that edited `e2e/almanac.mjs`, `hooks/testing-floor-guard.py` reported `node check failed (exit 1)` with `ECONNREFUSED 127.0.0.1:25577` on attempts 1/3, 2/3 and 3/3, and only released the turn at the cap. Port 25577 is the RCON port of that repo's e2e server, which the session had deliberately stopped. The stderr is the e2e suite's own `Rcon.connect` failing, so the guard appears to execute the edited `.mjs` (a whole suite that boots bots and talks to a live server) as its "node check", not a syntax check. UNVERIFIED which command the guard runs: the check is to read `hooks/testing-floor-guard.py` and `hooks/_testing_floor_lib.py` for how `.mjs` files map to a check, and whether `node --check <file>` would be enough.

Same session passed that suite 18/18 on a private server before the edit's commit, so the failure was the check, not the code. CLAUDE.md says slow end-to-end suites are NOT part of the per-change floor.

## Approach

Make the node check a syntax-only `node --check <file>` for files under `e2e/`, `tests/e2e`, or anything matching the project's e2e directory, or skip running them entirely. Keep running real unit-test commands for non-e2e sources. Add a case to the hook's own self-test suite (`hooks/test_*.py`) for an `e2e/*.mjs` edit.

## Acceptance

- Editing `e2e/*.mjs` with no server running does not block the turn.
- A real syntax error in that file still does.
- The hook's self-test suites stay green.

## Notes

- Duplicate of 1163, merged during the cleanup-todos pass 2026-10-23. Same root cause (node row runs npm test in e2e, _testing_floor_lib.py:350-362 and :485-512); its 2026-10-22 port 25577 recurrence and syntax-error acceptance were folded into 1163 Context.
