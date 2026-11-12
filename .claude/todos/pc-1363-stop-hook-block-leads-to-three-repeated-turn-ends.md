<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits are other hooks (auto-commit, chained shell, em dash, disconnected MCP tools, devnull false positives); none is a block answered by repeated turn ends -->
# A blocking Stop hook makes the model end the turn three times, repeating its status call and message

**Type:** skill-improvement
**Origin:** dev
**Summary:** When a Stop hook blocks the end of a turn, the model should answer it once instead of ending the turn again up to three times with the same status and message.

## Why

Joe, 2026-11-10 (in the claude_usage_in_taskbar repo, todo pc-1698): "we seem to be duplicating some stuff, i wonder if we should myb add a todo to look into this, see if we are doing all these things efficiently or if we are duplicating some events or whatever". The screenshot showed one turn ending with two identical `report_turn_status(done)` calls after the testing-floor Stop hook blocked three times (attempt 1/3, 2/3, 3/3).

## Goal

A Stop hook that blocks gets one considered answer, not up to three full turn ends that each repeat `report_turn_status` and a chat message.

## Context

- Measured 2026-11-12 in claude_usage_in_taskbar's `daemon.log`: 868 of 3703 `/turn/report-status` calls (23%) repeat the previous state for the same session, none within one second, 137 within 5 seconds. The quiet 10-minute window 2026-11-12 00:10-00:19 UTC had 28 `/hooks/stop` hits. Consistent with blocked turn ends, not proven to be only that.
- The blocking hook named in the incident is the testing-floor Stop hook in this repo's `hooks/`. UNVERIFIED which hook file and how its message words the retry; read it first.
- Writing to `hooks/` is a hard stop for a subagent dispatch (sensitive-file-guard asks), so this runs on the main thread with Joe present.

## Approach

1. Read the testing-floor Stop hook and its block message.
2. Make the block message say what one action satisfies it (run the named check, or state why it does not apply) and that the status call and chat message must not be repeated.
3. Optionally have the hook remember it already blocked this turn and not count a repeat status call as new work.

## Acceptance

- A blocked turn end is followed by at most one more `report_turn_status` for that turn in a test or a live check.
- The hook still blocks a turn that skipped the floor.
