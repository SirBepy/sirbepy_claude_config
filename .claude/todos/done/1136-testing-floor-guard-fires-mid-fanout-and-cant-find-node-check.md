<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 427 (done) built this gate; this is a defect in the shipped gate, the other hits only share vocabulary -->
# testing-floor-guard blocks an orchestrator turn mid-fan-out, and its node check cannot launch

**Type:** task
**Origin:** ai

## Goal

The Stop-hook testing floor only fires when there is something finished to verify, and its node
check actually runs on Windows.

## Context

Seen 2026-10-08 in cueline (`/loop-todos`, session 3c23586b). The orchestrator committed one todo,
then ended its turn while two background builders were still editing `src/` and `src-tauri/`.
`hooks/testing-floor-guard.py` blocked the stop with:

`rust: check timed out after 300s | node: check command not found ([WinError 2] The system cannot find the file specified)`

- The rust timeout coincided with a builder's concurrent cargo build in the same crate (cueline's
  builders use `CARGO_TARGET_DIR=D:/cargo-target-cueline`; UNVERIFIED which target dir the hook's
  check uses, would check `hooks/_testing_floor_lib.py`).
- The node failure is the hook itself: `[WinError 2]` is Python's subprocess failing to launch the
  check command. UNVERIFIED cause, likely `npm`/`pnpm` launched without the `.cmd` suffix or
  `shell=True` on Windows; would check how `_testing_floor_lib.py` builds the node command.
- The session's turn status was `working` with live background agents, so the floor ran against
  half-written builder output.

## Approach

1. Fix the node check launch on Windows (resolve `npm.cmd`/`pnpm.cmd` via `shutil.which`).
2. Skip, or defer, the floor when the turn ends while background agents in the session are still
   running, since their edits are not finished.

## Acceptance

- A cueline-shaped repo's node check runs on Windows from the hook.
- An orchestrator ending a turn with live background builders is not blocked by their in-progress
  edits.

## Notes

- Both halves fixed in the main thread, 2026-10-08. Node: run_stack_check resolves the launcher via shutil.which, so npm/pnpm/yarn .cmd shims launch (bare 'npm' reproduced WinError 2, resolved npm.CMD ran --version exit 0). Mid-fan-out: the guard defers (allows the turn, keeps the flag) while running_background_agents() finds a live builder in the transcript; last event per agent id wins (Agent launch or SendMessage resume = running, a task-notification naming it = stopped; notifications are queue-operation/attachment entries). On this session's own live transcript it returned exactly the one resumed builder. 7 new cases in hooks/test_testing_floor_guard.py, RED then GREEN.
