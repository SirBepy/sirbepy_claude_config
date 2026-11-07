<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md --><!-- duplicate-checked: pc-1308 is about close text reaching Joe, not the Stop guard; no existing todo covers the testing-floor Stop hook holding a /close open -->
# testing-floor-guard keeps a /close session alive when the check fails for an infra reason

**Type:** task
**Origin:** dev
**Summary:** A `/close` that called `close_session` still did not close, because `hooks/testing-floor-guard.py` blocked the turn end on a rust check that failed from a full disk, not from the change.

## Why

Joe, 2026-11-04, claude_usage_in_taskbar: "again... you didnt close even tho you say you did... log this and then actually close. idk why this has been happening so often lately".

## Goal

A session that has already called `close_session` is never held open by the testing-floor Stop guard, and a check that fails for an environment reason (no disk space, access violation in a build script) is not reported to Claude as "fix the failure".

## Context

- Reproduced 2026-11-04. The turn edited only `src/shared/chat/chat-turn-footer.css` and `e2e/view-harness/turn-meta-hover.view.spec.ts`. `/close` ran, `close_session` returned "will end at turn completion", then the Stop hook ran `cargo check` over `src-tauri` and blocked (attempt 1/3). The host only ends the session when the turn completes, so a blocked Stop means the chat stays open although Claude reported it closing.
- The failure was environmental: `D:` was 100% full (1.7M free of 932G), so `cargo check` died with "There is not enough space on the disk. (os error 112)" and, in the hook's own run, `STATUS_ACCESS_VIOLATION` (0xc0000005) from a build script. The node check passed. No Rust file was touched.
- `hooks/testing-floor-guard.py` already fails open on its own import errors and after 3 attempts, but each attempt re-runs the full cargo check, which takes minutes on a full disk, and a `/close` turn spends them one at a time.
- The only documented hatches are a global env var or the global skip-flag file `hooks/.testing-floor-skip`, which disables the guard for every session.

## Approach

- In `hooks/testing-floor-guard.py` `evaluate()`: allow the turn to end, without running checks, when this turn already called the `close_session` MCP tool (read it from the payload transcript the same way `last_turn_status` reads `report_turn_status`). A closing session has no later turn in which to fix anything.
- In `hooks/_testing_floor_lib.py` `run_checks`: classify output containing `os error 112`, `not enough space`, or `0xc0000005` as an infra failure. Treat it as a pass that prints one warning line naming the cause, so Claude reports "could not verify, disk full" instead of looping.
- Add cases for both to the hook's existing self-test suite, and run `python ci/run_all.py` (this is a Stop hook: a misfire blocks every session, per the module docstring).

## Acceptance

- A turn that ends after `close_session` is never blocked by this guard, even with a red check.
- A cargo check that fails with a disk-full or access-violation signature does not produce a block.
- A real compile error still blocks exactly as before.
